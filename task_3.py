import random

students = [
    "Kiruthiga", "Kiran", "Abinaya", "Varuni", "Swathi", "Monisha", "Adlin", "Arjun",
    "Sanjana", "Deepak", "Harini", "Rohit", "Divya", "Vignesh", "Shruti", "Naveen",
    "Priya", "Surya", "Meera", "Ananya", "Rahul", "Lavanya", "Vikram", "Preethi",
    "Akash", "Ishwarya", "Siddharth", "Sneha", "Manoj", "Kavya", "Rajesh", "Bhavya",
    "Rakesh", "Aishwarya", "Yash", "Vaishnavi", "Pranav", "Janani", "Ajay", "Pavithra",
    "Aravind", "Dhivya", "Karthik", "Revathi", "Balaji", "Deeksha", "Sathish", "Nithya",
    "Vinoth", "Sindhu"
]


subjects = ["Math", "Physics", "English"]

with open("students.txt", "w") as f:
    for student in students:
        scores = [random.randint(50, 100) for _ in subjects]
        record = [f"{student}"] + [f"{sub},{score}" for sub, score in zip(subjects, scores)]
        f.write(",".join(record) + "\n")

print(" Sample data (students.txt) generated.")


data = {}
with open("students.txt", "r") as f:
    for line in f:
        parts = line.strip().split(",")
        name = parts[0]
        scores = {parts[i]: int(parts[i+1]) for i in range(1, len(parts), 2)}
        data[name] = scores



def get_grade(avg):
    if avg >= 90:
        return "A"
    elif avg >= 80:
        return "B"
    elif avg >= 70:
        return "C"
    elif avg >= 60:
        return "D"
    else:
        return "F"

student_summary = {}

for student, scores in data.items():
    avg = sum(scores.values()) / len(scores)
    grade = get_grade(avg)
    best_subject = max(scores, key=scores.get)
    worst_subject = min(scores, key=scores.get)
    student_summary[student] = {
        "average": avg,
        "grade": grade,
        "best": best_subject,
        "worst": worst_subject,
        "scores": scores
    }


subject_averages = {sub: sum(stu["scores"][sub] for stu in student_summary.values()) / len(student_summary)
                    for sub in subjects}

highest_avg_subject = max(subject_averages, key=subject_averages.get)

above_avg_counts = {sub: sum(1 for stu in student_summary.values() if stu["scores"][sub] > subject_averages[sub])
                    for sub in subjects}

students_needing_help = [name for name, stu in student_summary.items() if stu["average"] < 75]



with open("report.txt", "w") as f:
    f.write("=== Student Performance Report ===\n\n")
    f.write("---- Individual Student Results ----\n")
    for name, details in student_summary.items():
        f.write(f"{name}: Avg={details['average']:.2f}, Grade={details['grade']}, "
                f"Best={details['best']}, Worst={details['worst']}\n")
    f.write("\n---- Class Analysis ----\n")
    f.write("Subject Averages:\n")
    for sub, avg in subject_averages.items():
        f.write(f"{sub}: {avg:.2f}\n")
    f.write(f"\nHighest Class Average Subject: {highest_avg_subject}\n")
    f.write("\nStudents Above Class Average Per Subject:\n")
    for sub, count in above_avg_counts.items():
        f.write(f"{sub}: {count} students\n")
    f.write("\nStudents Needing Help (avg < 75):\n")
    f.write(", ".join(students_needing_help) if students_needing_help else "None")
    f.write("\n")

print(" Report generated (report.txt).")