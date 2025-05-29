import numpy as np

# Array creation
a = np.array([1, 2, 3])
b = np.arange(4, 10)
c = np.linspace(0, 1, 5)

print("Array a:", a)
print("Array b (arange):", b)
print("Array c (linspace):", c)

# Element-wise operations
print("a * 10:", a * 10)
print("a + b[:3]:", a + b[:3])

# Broadcasting
d = np.ones((3, 1))
e = np.ones((1, 4))
print("Broadcasted sum (3x1 + 1x4):\n", d + e)

# Matrix multiplication
m1 = np.array([[1, 2], [3, 4]])
m2 = np.array([[2, 0], [1, 2]])
print("Matrix multiplication (m1 @ m2):\n", m1 @ m2)

# Aggregations
data = np.random.randn(2, 5)
print("Random data:\n", data)
print("Mean of data:", np.mean(data))
print("Sum along axis 0:", np.sum(data, axis=0))

# Slicing and boolean indexing
arr = np.arange(10)
print("Sliced arr[::2]:", arr[::2])
print("Elements > 5:", arr[arr > 5])

# Utility: reshape, transpose
mat = np.arange(12).reshape(3, 4)
print("Original matrix:\n", mat)
print("Transposed:\n", mat.T)