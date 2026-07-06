CPI stack listener design
=========================

Issue #647 proposes CPI stack listeners that explain where core cycles are
spent. The goal is to let a ChampSim run report stage-level bottleneck
attribution without changing simulator behavior. This note scopes a minimal
listener-first design that can be reviewed before adding pipeline
instrumentation.

Problem statement
-----------------

ChampSim already reports aggregate IPC, branch statistics, cache statistics, and
heartbeat progress. These numbers say whether performance changed, but they do
not explain which core stage is limiting progress.

A CPI stack listener should observe selected core stages and attribute each
observed CPU cycle to one bottleneck reason. At the end of the simulation phase,
the listener can divide attributed cycles by retired instructions to report CPI
contribution by stage and reason.

Current listener API
--------------------

The current event listener path is intentionally small:

* ``inc/events.h`` defines ``BEGIN_PHASE`` and ``RETIRE``.
* ``inc/event_listeners.h`` stores the listener tuple, activates listeners from
  ``--listeners``, and dispatches ``handle_event<Event>(...)``.
* ``inc/listeners/heartbeat.h`` listens to ``BEGIN_PHASE`` and ``RETIRE``.
* ``src/champsim.cc`` emits ``BEGIN_PHASE`` before each phase.
* ``src/ooo_cpu.cc`` emits ``RETIRE`` from ``O3_CPU::retire_rob`` with the CPU
  id, retired ROB iterator range, and current cycle.

That API is enough for instruction and cycle counts, but not enough for CPI
stacks. CPI stacks need stage state even when no instruction retires.

Proposed minimal API
--------------------

Add a stage-sample event that reports one classified stage observation per CPU
cycle:

.. code-block:: cpp

   enum Event {
     BEGIN_PHASE,
     END_PHASE,
     RETIRE,
     CORE_STAGE_SAMPLE
   };

   enum class core_stage {
     dispatch,
     issue,
     retire
   };

   enum class cpi_stack_reason {
     active,
     empty,
     not_ready,
     rob_full,
     lq_full,
     sq_full,
     register_dependency,
     register_file_full,
     memory_dependency,
     head_not_complete,
     width_limit,
     unknown
   };

   struct core_stage_sample {
     uint32_t cpu;
     uint64_t cycle;
     core_stage stage;
     cpi_stack_reason reason;
     long progress;
     long width;
     bool warmup;
   };

``CORE_STAGE_SAMPLE`` should be observational. It should not feed back into
scheduling decisions, queue insertion, branch recovery, memory ordering, or
statistics already used by the simulator.

An ``END_PHASE`` event is also useful because CPI stacks need a clean flush point
for simulation-phase output. The existing ``BEGIN_PHASE`` event is enough to
reset listener state at phase boundaries, but it does not tell listeners when all
CPUs have completed a phase.

Stage attribution
-----------------

Dispatch
  ``O3_CPU::dispatch_instruction`` has enough local state to produce a first
  useful dispatch stack. It can distinguish an empty dispatch buffer, an
  instruction that is not ready yet, a full ROB, insufficient LQ entries,
  insufficient SQ entries, and active dispatch. If multiple constraints are true
  in the same cycle, the listener should receive the first blocking reason in a
  documented priority order.

Issue
  ChampSim separates scheduling and execution in ``O3_CPU::schedule_instruction``
  and ``O3_CPU::execute_instruction``. A minimal issue stack should start at
  ``execute_instruction`` because that is where scheduled instructions are
  issued for execution. Available reasons include no ready scheduled
  instruction, source register dependency, and execution width consumed. A later
  refinement can add a separate scheduling stack for register allocation and
  rename pressure.

Retire
  ``O3_CPU::retire_rob`` already computes the range retired this cycle. If the
  range is empty, it can classify the reason as an empty ROB or an incomplete
  ROB head. If the range is non-empty, the cycle is active for the retire stage.

Data currently available
------------------------

The current core model exposes enough state for a conservative first pass:

* Per-CPU current cycle through ``current_time / clock_period``.
* Per-CPU warmup state through ``operable::warmup``.
* Dispatch buffer occupancy and front instruction readiness.
* ROB occupancy and ROB capacity.
* LQ/SQ occupancy and instruction memory operand counts.
* Register allocator free register count and source register validity.
* Retire span and retired instruction count.

Data still missing for accuracy
-------------------------------

The first implementation should document these limitations:

* Several bottlenecks can be true in the same cycle; a CPI stack needs a stable
  priority policy.
* Some stalls are caused by earlier stages, but are observed at a later stage as
  ``empty`` or ``not_ready``.
* The current issue path does not expose a single named "issue" stage. It is
  split across scheduling, execution, memory scheduling, and LSQ operation.
* Memory dependency reasons need more detail to distinguish cache miss latency,
  translation delay, store forwarding, MSHR pressure, and bus backpressure.
* CPI stack attribution is approximate by design; it should be treated as a
  diagnostic guide, not a proof of exact causality.

Output schema
-------------

JSON output should be machine-readable and stable:

.. code-block:: json

   {
     "schema_version": 1,
     "listener": "cpi_stack",
     "phase": "Simulation",
     "cpus": [
       {
         "cpu": 0,
         "retired_instructions": 1000000,
         "stages": {
           "dispatch": {
             "cycles": 100000,
             "reasons": {
               "active": {"cycles": 65000, "cpi": 0.065},
               "rob_full": {"cycles": 12000, "cpi": 0.012}
             }
           }
         }
       }
     ]
   }

A CSV artifact can use one row per reason:

.. code-block:: text

   phase,cpu,stage,reason,cycles,retired_instructions,cpi
   Simulation,0,dispatch,rob_full,12000,1000000,0.012

The listener should avoid printing every cycle. It should aggregate in memory and
emit final JSON/CSV at phase end or program end.

Implementation plan
-------------------

PR 1: design note only
  Document the listener API, event placement, limitations, and PR sequence.

PR 2: event types and no-op listener
  Add ``CORE_STAGE_SAMPLE`` and ``END_PHASE`` events, a payload struct, and a
  disabled/no-op CPI stack listener that can be selected with ``--listeners``.
  Unit-test event dispatch without changing core behavior.

PR 3: dispatch-stage attribution
  Instrument ``O3_CPU::dispatch_instruction``. Emit dispatch samples and produce
  JSON/CSV output for dispatch reasons only.

PR 4: issue and retire attribution
  Add conservative issue and retire samples. Keep reason priority documented and
  fixture-test output determinism.

PR 5: automation integration
  Upload CPI stack artifacts in a manual or opt-in benchmark/report workflow.
  Do not gate CI on CPI stack values until maintainers have reviewed noise and
  trace sensitivity.

Risks
-----

* Calling listeners from hot core paths can add overhead. The first listener
  should aggregate simple integer counters and stay disabled unless requested.
* Event payloads can become unstable if they expose too much internal state.
  Prefer small enums and counts over passing mutable core structures.
* The CPI stack reason priority can bias interpretation. The priority order must
  be documented and tested.
* Warmup and simulation phases must be separated, otherwise warmup behavior will
  pollute reported CPI attribution.
* JSON/CSV files should be artifacts, not PR comments, until maintainers choose
  the expected reporting workflow.
