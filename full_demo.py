# examples/full_demo.py
# Run with: python src/interpreter.py examples/full_demo.py
# Or via the demo: streamlit run src/demo.py

# ── Variables & Types ─────────────────────────────────────────────────────────
x: int = 42
y: float = 3.14
name: str = "Alice"
flag: bool = True
nothing = None

print("=== Variables ===")
print(x, y, name, flag, nothing)
print(type(x), type(y), type(name))

# ── Strings ──────────────────────────────────────────────────────────────────
print("\n=== Strings ===")
s = "Hello, Python!"
print(len(s))
print(s.upper())
print(s[0:5])
print(s.replace("Python", "World"))
words = s.split(", ")
print(words)
print(", ".join(words))

# ── Booleans ─────────────────────────────────────────────────────────────────
print("\n=== Booleans ===")
print(True and False)
print(True or False)
print(not True)
print(bool(0), bool(1), bool(""), bool("hi"))

# ── Operators ────────────────────────────────────────────────────────────────
print("\n=== Operators ===")
a, b = 10, 3
print(a + b, a - b, a * b, a / b, a // b, a % b, a ** b)
print(a & b, a | b, a ^ b, a << 1, a >> 1)

# ── If/Elif/Else ──────────────────────────────────────────────────────────────
print("\n=== If/Elif/Else ===")
score = 85
if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
else:
    print("F")

# ── While ────────────────────────────────────────────────────────────────────
print("\n=== While ===")
i = 1
while i <= 5:
    print(i, end=" ")
    i += 1
print()

# ── For + Range ───────────────────────────────────────────────────────────────
print("\n=== For + Range ===")
for n in range(1, 6):
    print(n, end=" ")
print()

total = 0
for n in range(1, 101):
    total += n
print("Sum 1-100:", total)

# ── Lists ────────────────────────────────────────────────────────────────────
print("\n=== Lists ===")
fruits = ["apple", "banana", "cherry"]
fruits.append("date")
fruits.insert(1, "blueberry")
fruits.remove("banana")
print(fruits)
print(sorted(fruits))
print("cherry" in fruits)

evens = [x for x in range(10) if x % 2 == 0]
print(evens)

# ── Tuples ───────────────────────────────────────────────────────────────────
print("\n=== Tuples ===")
point = (10, 20, 30)
px, py, pz = point
print(px, py, pz)
print(point[1:])

# ── Sets ─────────────────────────────────────────────────────────────────────
print("\n=== Sets ===")
a_set = {1, 2, 3, 4}
b_set = {3, 4, 5, 6}
print(a_set | b_set)
print(a_set & b_set)
print(a_set - b_set)

# ── Dicts ────────────────────────────────────────────────────────────────────
print("\n=== Dicts ===")
person = {"name": "Alice", "age": 30}
person["city"] = "NYC"
print(person)
print(person.get("missing", "N/A"))
for k, v in person.items():
    print(k, "->", v)

# ── Functions ────────────────────────────────────────────────────────────────
print("\n=== Functions ===")

def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def greet(name: str, greeting: str = "Hello") -> str:
    return greeting + ", " + name + "!"

print(factorial(10))
print(greet("Bob"))
print(greet("Alice", "Hi"))

# ── Lambda & Higher-order ─────────────────────────────────────────────────────
print("\n=== Lambda ===")
double = lambda x: x * 2
print(list(map(double, [1,2,3,4,5])))
print(list(filter(lambda x: x % 2 == 0, range(10))))
print(sorted([5,2,8,1,9], key=lambda x: -x))

# ── Range & Iterators ────────────────────────────────────────────────────────
print("\n=== Iterators ===")
for i, v in enumerate(["a", "b", "c"], start=1):
    print(i, v)

for a, b in zip([1,2,3], ["x","y","z"]):
    print(a, b)

it = iter([10, 20, 30])
print(next(it))
print(next(it))

# ── Match/Case ────────────────────────────────────────────────────────────────
print("\n=== Match/Case ===")

def classify(n):
    match n:
        case 0:
            return "zero"
        case 1:
            return "one"
        case _:
            return "many"

for n in [0, 1, 42]:
    print(classify(n))

# ── Classes ───────────────────────────────────────────────────────────────────
print("\n=== Classes ===")

class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound

    def speak(self):
        return self.name + " says " + self.sound

class Dog(Animal):
    def __init__(self, name):
        self.name = name
        self.sound = "woof"

    def fetch(self, item):
        return self.name + " fetches " + item

dog = Dog("Rex")
print(dog.speak())
print(dog.fetch("ball"))

# ── Try/Except ───────────────────────────────────────────────────────────────
print("\n=== Try/Except ===")

def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return "Cannot divide by zero"
    finally:
        print("division attempted")

print(safe_divide(10, 2))
print(safe_divide(10, 0))

# ── Arrays (2D) ───────────────────────────────────────────────────────────────
print("\n=== 2D Arrays ===")
matrix = [[i * 3 + j for j in range(3)] for i in range(3)]
for row in matrix:
    print(row)

print("\nAll done!")
