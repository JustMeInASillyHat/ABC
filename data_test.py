import os

for item in os.listdir():
    if item.endswith(".xlsx"):
        print(f"- {item}")