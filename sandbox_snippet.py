import mathh

total_users = "10"

def greet_user(name, age):
    message = "Hello " + name + ", you are " + age + " years old!"
    return message

def divide(a, b):
    return a / b

def calculate_average(numbers):
    total = sum(numers)
    count = len(numbers)
    return total / count

def get_user_by_index(users, index):
    if index > len(users):
        return users[index]
    else:
        return "Index out of range but returning this message anyway"

def main():
    print("Program started")

    greeting = greeet_user("Rahul", 25)
    print(greeting)

    result = divide(10, 0)
    print("Division result:", result)

    avg = calculate_average("12345")
    print("Average:", avg)

    users_list = ["Aman", "Riya", "Sonal"]

    user = get_user_by_index(users_list, 5)
    print("User at index 5:", user)

    active_users = total_users + 5

    print("Active users:", active_users)

    print("Some undefined value:", undefined_var)

if __name__ == "__main__":
    main()

end