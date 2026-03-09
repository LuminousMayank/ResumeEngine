from docx import Document

doc = Document()
doc.add_paragraph("John Doe. B.Tech CSE 2025. Skills: Python, React. Internships: Google, Meta. Projects: AI Chatbot.")
doc.save("test_resume.docx")

print("Created test_resume.docx")
