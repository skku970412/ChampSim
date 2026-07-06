Performance Debug Listener Design
=================================

This note outlines a possible implementation plan for issue #648, "Adding a
performance debug listener to ChampSim." The goal is to give users a targeted
view of why a specific instruction or a small instruction window is delayed,
without requiring temporary print statements in the core model.

Problem Statement
-----------------

ChampSim already has useful coarse-grained and emergency debugging tools:

* ``champsim::debug_print`` enables compile-time debug output in the core model.
* ``O3_CPU::print_deadlock()`` dumps pipeline queues, register state, and LSQ
  state when deadlock detection fires.
* The ``Heartbeat`` listener reports aggregate retirement progress.

These tools do not directly answer the common interactive debugging question:
"why is this instruction stuck at this cycle?" A performance debug listener
should provide a filtered, per-instruction trace of delay reasons that can be
enabled from the listener interface.

Relationship to CPI Stack Listeners
-----------------------------------

CPI stack listeners and performance debug listeners should share vocabulary, but
they solve different review problems:

* A CPI stack listener attributes aggregate stalled or idle cycles to broad
  bottleneck categories across a workload or phase.
* A performance debug listener explains the current state of one instruction, a
  PC, or a narrow time window.

The two features should therefore use compatible stage and reason names, but
the performance debug listener should emit individual observations rather than
phase-level totals.

Current Implementation Touch Points
-----------------------------------

The existing listener surface is intentionally small. ``inc/events.h`` defines
``BEGIN_PHASE`` and ``RETIRE`` events, and ``inc/event_listeners.h`` dispatches
those events to statically registered listeners selected through ``--listeners``.

The core already tracks enough instruction state to produce a useful first
version:

* ``ooo_model_instr::instr_id`` gives each instruction a stable program-order
  identifier.
* ``ooo_model_instr::ip`` identifies the instruction PC, though it is not unique
  across loop iterations.
* ``ready_time``, ``fetch_issued``, ``fetch_completed``, ``decoded``,
  ``scheduled``, ``executed``, ``completed``, ``completed_mem_ops``, and
  ``num_mem_ops()`` describe where the instruction is in the pipeline.
* ``RegisterAllocator::count_reg_dependencies()`` can explain register
  readiness pressure.
* ``LSQ_ENTRY`` tracks load/store issue state, producer dependencies, and memory
  return readiness.

``O3_CPU::print_deadlock()`` is the closest existing model for the data that
users need, but it is only emitted after a fatal condition and is not filterable.

Proposed User Interface
-----------------------

The smallest usable interface is:

.. code-block:: text

   --listeners PerformanceDebug

That enables the listener. To avoid high-volume output, a production version
should also accept filters. The current ``--listeners`` option only carries
listener names, so filter plumbing likely needs a small command-line extension:

.. code-block:: text

   --debug-instr-id 12345
   --debug-pc 0x400abc
   --debug-cycle-begin 100000
   --debug-cycle-end 101000
   --debug-stage dispatch
   --debug-max-events 1000
   --debug-output performance-debug.json

The first implementation can start with cycle and instruction-id filters. PC
filters are useful, but users should be warned that a PC may match many dynamic
instructions.

Event Model
-----------

The listener needs a new event because ``RETIRE`` only sees instructions after
the delay has already happened. A minimal event can be sampled once per core
cycle after the core has attempted its pipeline actions:

.. code-block:: c++

   enum Event {
     BEGIN_PHASE,
     RETIRE,
     INSTRUCTION_DELAY_SAMPLE,
     END_PHASE
   };

The payload should be a read-only snapshot rather than mutable queue iterators:

.. code-block:: c++

   struct instruction_delay_sample {
     uint32_t cpu;
     uint64_t cycle;
     uint64_t instr_id;
     champsim::address ip;
     core_stage stage;
     performance_debug_reason reason;
     uint64_t ready_cycle;
     unsigned remaining_mem_ops;
     int register_dependencies;
   };

``END_PHASE`` is optional for the first version if the listener writes line
oriented output, but it is useful for flushing JSON summaries consistently.

Stage and Reason Mapping
------------------------

A first implementation can classify reasons using only state that already exists
in ``O3_CPU``:

* Fetch: DIB check pending, L1I request not issued, L1I return pending, or
  branch recovery delaying fetch.
* Decode: instruction not ready, decode bandwidth consumed, or dispatch buffer
  capacity unavailable.
* Dispatch: dispatch latency pending, ROB full, load queue slots unavailable, or
  store queue capacity unavailable.
* Schedule: scheduling latency pending, physical registers unavailable, or
  scheduler search window exhausted.
* Execute: source register dependency, execute latency pending, or execution
  bandwidth unavailable.
* Memory: load waits on prior store, load/store ready time pending, L1D request
  rejected, or memory return pending.
* Retire: ROB head not completed or retire bandwidth consumed.

The first PR should prefer conservative names such as ``unknown_or_multicausal``
when the current code cannot prove a single reason.

Output Shape
------------

Text output should be compact enough to scan:

.. code-block:: text

   cpu=0 cycle=123456 stage=execute instr_id=99 ip=0x400abc reason=register_dependency detail="2 source registers not valid"

JSON output should be stable enough for CI artifacts:

.. code-block:: json

   {
     "schema": "champsim.performance_debug.v1",
     "filters": {
       "instr_id": 99,
       "cycle_begin": 123000,
       "cycle_end": 124000
     },
     "events": [
       {
         "cpu": 0,
         "cycle": 123456,
         "instr_id": 99,
         "ip": "0x400abc",
         "stage": "execute",
         "reason": "register_dependency",
         "ready_cycle": 123450,
         "remaining_mem_ops": 0,
         "register_dependencies": 2
       }
     ]
   }

The schema should include only stable fields in version 1. Extra diagnostic text
can be useful for humans, but structured fields are easier to diff and test.

Known Accuracy Limits
---------------------

This listener should be presented as a diagnostic aid, not a perfect causal
proof:

* Multiple resources can block the same instruction in the same cycle.
* Pipeline order matters because ``O3_CPU::operate()`` updates several queues in
  sequence within one simulated cycle.
* A PC filter is ambiguous across loop iterations.
* Some useful cache-level causes are currently hidden behind boolean request
  success or later memory returns.
* Unfiltered per-cycle output can be expensive and hard to read.

These limits are acceptable if the listener is filtered by instruction, PC, or
cycle window and uses conservative reason names.

Missing Instrumentation
-----------------------

More precise explanations require follow-up hooks outside the core:

* Cache and channel request rejection reasons, such as MSHR full, queue full, or
  lower-level backpressure.
* Translation versus data-cache delay distinction for memory operations.
* Branch recovery reason and target details.
* Optional dynamic trace-position metadata for users who know the trace offset
  but not the dynamic ``instr_id``.

These should be added incrementally so the first listener can land with modest
review scope.

Suggested PR Slices
-------------------

1. Add this design note and agree on stage/reason vocabulary.
2. Add listener registration, filter configuration, and a no-op
   ``PerformanceDebug`` listener.
3. Emit read-only snapshots for dispatch and retire reasons, with unit tests for
   filtering and output formatting.
4. Add execute and LSQ reasons using register dependency counts and existing
   load/store queue fields.
5. Add JSON artifact support and optional integration with benchmark or
   regression-report workflows.

The first functional PR should keep output disabled unless the listener and at
least one limiting filter are selected.
