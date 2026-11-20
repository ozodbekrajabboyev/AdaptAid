# Worked example: checking balanced brackets

**Problem.** A code editor highlights unmatched brackets. Write `is_balanced(text)` that returns `True` when every `(`, `[` and `{` is closed by the matching bracket in the right order, ignoring all other characters. For example `{a[b(c)]d}` is balanced, while `(a]` and `((b)` are not.

## Step 1: see why a counter is not enough

Counting openers and closers catches `((b)`, but `([)]` has two of each and is still wrong: the `)` arrives while `[` is the most recently opened bracket. The bracket that must be closed next is always the **most recent unmatched opener**, and "most recent first" is exactly what a stack gives you.

## Step 2: the algorithm

1. Start with an empty stack.
2. For each character:
   - an opening bracket: push it;
   - a closing bracket: if the stack is empty, fail (there is nothing to close); otherwise pop, and fail if the popped opener is not the matching type;
   - anything else: ignore it.
3. At the end, succeed only if the stack is empty (no opener left unclosed).

## Step 3: the code

```python
PAIRS = {")": "(", "]": "[", "}": "{"}

def is_balanced(text):
    stack = []
    for ch in text:
        if ch in "([{":
            stack.append(ch)                  # push the opener
        elif ch in ")]}":
            if not stack or stack.pop() != PAIRS[ch]:
                return False                  # nothing to close, or wrong type
    return not stack                          # leftovers are unclosed openers
```

## Step 4: trace a balanced string, `{[()()]}`

| Step | Char | Action | Stack (bottom → top) |
|---|---|---|---|
| 1 | `{` | push | `{` |
| 2 | `[` | push | `{ [` |
| 3 | `(` | push | `{ [ (` |
| 4 | `)` | pop `(`: matches | `{ [` |
| 5 | `(` | push | `{ [ (` |
| 6 | `)` | pop `(`: matches | `{ [` |
| 7 | `]` | pop `[`: matches | `{` |
| 8 | `}` | pop `{`: matches | (empty) |

The string has ended and the stack is empty, so the result is **`True`**.

## Step 5: trace the crossed string, `([)]`

| Step | Char | Action | Stack (bottom → top) |
|---|---|---|---|
| 1 | `(` | push | `(` |
| 2 | `[` | push | `( [` |
| 3 | `)` | pop `[`, but `)` needs `(`: **mismatch** | `(` |

The function returns **`False`** at step 3 without reading the rest.

## Step 6: the three ways to fail

| Input | What happens | Failure |
|---|---|---|
| `([)]` | `)` pops `[` | wrong type |
| `())` | the third character `)` finds the stack empty | closer with nothing open |
| `((b)` | the text ends with `(` still on the stack | opener never closed |

## Result

Each character is pushed and popped at most once: **O(n) time**. In the worst case, a string of openers such as `((((`, the stack holds n items: **O(n) extra space**.
