import copy
import time

# 1. Immutable Example (Strings)
print("1. Immutable Example (Strings)")
a = "Hello"
b = a
print(a == b)  # True (same value)
print(a is b)  # True, because small strings are interned
print(id(a), id(b))

# Now try changing one of them
b = "World"
print(a == b)  # False (values are different now)
print(a is b)  # False, since they are now different objects
print(id(a), id(b))  # Different memory locations

# 2. Immutable Example (Tuples)
print("\n2. Immutable Example (Tuples)")
a = (1, 2, 3)
b = a
print(a == b)  # True (same value)
print(a is b)  # True (same reference)
print(id(a), id(b))

# Modifying a tuple (which will raise an error)
try:
    a[0] = 100
except TypeError as e:
    print("Error:", e)

# 3. Mutable Example (List)
print("\n3. Mutable Example (List)")
a = [1, 2, 3]
b = a
b[0] = 100  # Modify the list
print("a:", a)  # a changed because both a and b refer to the same list
print("b:", b)
print(id(a), id(b))  # Same memory address, so they point to the same list
print(a is b)  # True, same object

# Adding another element
b.append(4)
print("a after append:", a)  # a changes as well
print("b after append:", b)

# 4. Shallow Copy (List)
print("\n4. Shallow Copy (List)")
a = [1, 2, 3]
b = a.copy()  # Shallow copy of list
b[0] = 100
print("a:", a)  
print("b:", b)  
print(id(a), id(b))  # Different memory addresses
print(a is b)  # False, different objects

# 5. Deep Copy (Nested List)
print("\n5. Deep Copy (Nested List)")
a = [[1, 2], [3, 4]]
b = copy.deepcopy(a)  # Deep copy
b[0][1] = 100
print("a:", a)  # a is unaffected
print("b:", b)  # b changed
print(id(a), id(b))  # Different memory addresses
print(id(a[0]), id(b[0]))  # Different objects inside the list

# 6. Mutable and Immutable Comparison (Dict and Set)
print("\n6. Mutable and Immutable Comparison (Dict and Set)")
a = {"key": "value"}
b = a
print(a == b)  # True (same value)
print(a is b)  # True (same reference)

b["key"] = "new value"
print(a)  # a is modified, since both reference the same object

# Using set, which is mutable
a_set = {1, 2, 3}
b_set = a_set
b_set.add(4)
print("a_set:", a_set)  # Changes reflected in a_set
print("b_set:", b_set)

# 7. String Interning
print("\n7. String Interning")
a = "hello"
b = "hello"
print(a == b)  # True, because the values are the same
print(a is b)  # True, because Python optimizes memory by interning small strings

c = "hello world"
d = "hello" + " world"
print(c == d)  # True
print(c is d)  # False, because this string was dynamically created, so it is not interned

# 8. Mutating vs Rebinding Variables
print("\n8. Mutating vs Rebinding Variables")
x = [1, 2, 3]
y = x
x = [4, 5, 6]  # x is now a different object, y still refers to the original list
print(x)  # [4, 5, 6]
print(y)  # [1, 2, 3]
print(id(x), id(y))  # Different memory locations now

# 9. Immutability in Function Arguments
print("\n9. Immutability in Function Arguments")
def modify_immutable(a):
    print(id(a))
    a += 1
    print(id(a))  # New object after modification (rebinds the reference)

x = 10
print(id(x))  # Original object id
modify_immutable(x)  # x is passed by value, so a new object is created inside the function
print(x)  # x remains unchanged outside the function

# 10. Performance of Mutable and Immutable Objects
print("\n10. Performance of Mutable and Immutable Objects")
# Immutable (string)
start_time = time.time()
s = "hello"
for _ in range(10**6):
    s += "!"
end_time = time.time()
print("Immutable operation time:", end_time - start_time)

# Mutable (list)
start_time = time.time()
lst = [1]
for _ in range(10**6):
    lst.append(0)
end_time = time.time()
print("Mutable operation time:", end_time - start_time)
