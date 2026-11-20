# Stacks

A **stack** is a collection where items are added and removed at one end only, called the **top**. The last item put in is the first one taken out: **LIFO** (last in, first out). Think of a pile of plates: you add plates on top and take them from the top.

## Operations

| Operation | What it does | Cost |
|---|---|---|
| `push(x)` | put x on top | O(1) |
| `pop()` | remove and return the top item | O(1) |
| `peek()` (or `top()`) | return the top item *without* removing it | O(1) |
| `is_empty()` | is there anything on the stack? | O(1) |

Popping or peeking an empty stack is an error called **underflow**. Pushing onto a full fixed-size stack is an **overflow**.

## Two implementations

**Array (Python list).** The end of the list is the top: `append` pushes, `pop()` pops and `s[-1]` peeks. All are O(1) (append is amortised O(1)).

```python
stack = []
stack.append("a")    # push
stack.append("b")    # push
print(stack[-1])     # peek -> b
print(stack.pop())   # pop  -> b
print(stack)         # ['a']
```

Using the *front* of the list as the top (`insert(0, x)` and `pop(0)`) still gives LIFO order, but every push and pop shifts all the other items: O(n).

**Linked list.** The head is the top. Push makes a new node whose `next` is the old head; pop returns the head's value and moves `head` to `head.next`. Both are O(1), and the stack never needs resizing, at the price of one extra reference per item.

## Applications

- **Balanced brackets.** Push each opening bracket; for each closing bracket, pop and check that the types match. At the end the stack must be empty.
- **Undo.** Each edit is pushed; Undo pops the most recent one.
- **The call stack.** When a function calls another, the caller is paused and its frame stays on the stack. The most recently called function finishes first, then its caller carries on from where it stopped.
- **Postfix expressions** such as `3 4 + 2 *`: push numbers; for an operator, pop two numbers, apply it, push the result. Here 3 + 4 = 7, then 7 × 2 = 14.
- **Reversing** a sequence: push every item, then pop them all.

## Common mistakes

- Popping without checking `is_empty()` first: `[].pop()` raises `IndexError`.
- Mixing ends: `append` with `pop(0)` removes the *oldest* item, which makes a queue, not a stack.
