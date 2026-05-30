"""Per-mutation-type LLM prompt templates."""

MUTATION_TYPES = {
    "add_arithmetic": {
        "label": "Add arithmetic instruction",
        "description": "Insert one new arithmetic instruction (add/sub/mul/sdiv)",
        "prompt_template": """You are an expert in LLVM IR. Your task is to mutate the following
LLVM IR for compiler differential testing.

MUTATION TASK: Insert exactly ONE new arithmetic instruction
(choose from: add, sub, mul, sdiv, srem, and, or, xor) somewhere
before the final ret instruction. The new instruction must:
- Define a fresh SSA name not already used in the IR
- Use existing SSA values or constants as operands
- Have matching i32 or i64 types on both operands
- Be used: update the ret to return the new value, OR use it
  in a subsequent instruction

Return ONLY the complete modified LLVM IR. No explanation,
no markdown fences, no commentary. Just raw IR text.

ORIGINAL IR:
{ir}
""",
    },
    "change_types": {
        "label": "Change integer types",
        "description": "Widen or narrow integer types (i32 ↔ i64)",
        "prompt_template": """You are an expert in LLVM IR. Your task is to mutate the following
LLVM IR for compiler differential testing.

MUTATION TASK: Change integer types consistently throughout the
function. Either:
  (a) widen all i32 to i64, adding sext/zext where needed, OR
  (b) narrow all i64 to i32, adding trunc where needed
Pick one strategy and apply it consistently. Update function
signature, all instructions, and the ret type to match.

Rules:
- All uses of a renamed SSA value must have matching types
- Add explicit sext, zext, or trunc cast instructions where types cross
- Do not leave any type mismatch

Return ONLY the complete modified LLVM IR. No explanation,
no markdown fences, no commentary. Just raw IR text.

ORIGINAL IR:
{ir}
""",
    },
    "insert_branch": {
        "label": "Insert conditional branch",
        "description": "Split a basic block and add an if-else branch",
        "prompt_template": """You are an expert in LLVM IR. Your task is to mutate the following
LLVM IR for compiler differential testing.

MUTATION TASK: Insert a conditional branch that splits the entry
block into two paths that merge at a new exit block. Steps:
  1. Add an icmp instruction comparing an existing SSA value to 0
  2. Add a br instruction branching to label %true_path or %false_path
  3. Create %true_path and %false_path blocks, each computing a
     slightly different result using existing values
  4. Add a final %merge block with a phi instruction that picks
     between the two results
  5. ret from %merge

All SSA names must be unique. All blocks must have terminators.
The phi node must list every predecessor.

Return ONLY the complete modified LLVM IR. No explanation,
no markdown fences, no commentary. Just raw IR text.

ORIGINAL IR:
{ir}
""",
    },
    "insert_phi": {
        "label": "Insert PHI node",
        "description": "Add a loop with a PHI node accumulator",
        "prompt_template": """You are an expert in LLVM IR. Your task is to mutate the following
LLVM IR for compiler differential testing.

MUTATION TASK: Wrap the body of the function in a simple counted
loop using PHI nodes. Steps:
  1. Create a %loop_header block with two PHI nodes:
       %i = phi i32 [ 0, %entry ], [ %i_next, %loop_body ]
       %acc = phi i32 [ 0, %entry ], [ %acc_next, %loop_body ]
  2. In %loop_body: compute %acc_next = add i32 %acc, <existing val>
     compute %i_next = add i32 %i, 1
     compute %cond = icmp slt i32 %i_next, 3
     branch back to %loop_header or fall to %exit
  3. In %exit: ret the final %acc PHI value

Every PHI must list ALL predecessor blocks. All SSA names unique.

Return ONLY the complete modified LLVM IR. No explanation,
no markdown fences, no commentary. Just raw IR text.

ORIGINAL IR:
{ir}
""",
    },
    "dead_code": {
        "label": "Insert dead code",
        "description": "Add unreachable instructions or unused definitions",
        "prompt_template": """You are an expert in LLVM IR. Your task is to mutate the following
LLVM IR for compiler differential testing.

MUTATION TASK: Insert dead code that is syntactically valid but
semantically unreachable or unused. Choose ONE of:
  (a) Add an 'unreachable' block: a new label that is never
      branched to, containing 1-2 valid instructions + unreachable
  (b) Add 2-3 new SSA definitions that are never used in any
      instruction or ret (dead definitions)

Rules:
- All new SSA names must be fresh and unique
- All new instructions must be type-correct
- The observable output of the function must NOT change
- Do not remove or alter any existing instruction

Return ONLY the complete modified LLVM IR. No explanation,
no markdown fences, no commentary. Just raw IR text.

ORIGINAL IR:
{ir}
""",
    },
    "swap_operands": {
        "label": "Swap / replace operands",
        "description": "Swap operand order or replace a constant operand",
        "prompt_template": """You are an expert in LLVM IR. Your task is to mutate the following
LLVM IR for compiler differential testing.

MUTATION TASK: Make one small operand-level change. Choose ONE:
  (a) For a commutative instruction (add, mul, and, or, xor):
      swap its two operands (result is semantically identical —
      this tests whether the optimiser normalises operand order)
  (b) For any instruction using an integer constant, replace that
      constant with a different small constant (e.g. 1 → 2, 0 → 1)
      Update any downstream uses if the type changes

Rules:
- Make exactly ONE change
- All types must remain consistent after the change
- Do not add or remove any SSA names

Return ONLY the complete modified LLVM IR. No explanation,
no markdown fences, no commentary. Just raw IR text.

ORIGINAL IR:
{ir}
""",
    },
}


def get_prompt(mutation_type: str, ir_text: str) -> str:
    entry = MUTATION_TYPES.get(mutation_type)
    if not entry:
        raise ValueError(f"Unknown mutation type: {mutation_type}")
    return entry["prompt_template"].format(ir=ir_text)
