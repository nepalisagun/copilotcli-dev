import os

# Create directories
os.makedirs('src', exist_ok=True)
os.makedirs('tests', exist_ok=True)
os.makedirs('.github/workflows', exist_ok=True)

print("Directories created")
