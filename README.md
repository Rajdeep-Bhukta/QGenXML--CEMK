# Moodle Question Editor

A Python-based desktop application for creating, editing, organizing, previewing, validating, and exporting Moodle-style question papers.

The application provides a graphical interface for managing questions and supports multiple question types, question groups, exam header information, images, Moodle XML export/import, and PDF question-paper generation.

## Features

* Create and manage multiple question files using tabs
* Create, edit, and delete questions
* Support for multiple question types:

  * Multiple Choice Question (MCQ)
  * Short Answer Question (SAQ)
  * Long Answer Question
* Assign marks to individual questions
* Insert questions at a specific position
* Add images to questions
* Preview questions with inline images
* Automatically remove image tags from displayed question text
* Add exam header information:

  * College Name
  * Department
  * Subject
  * Subject Code
  * Exam Name
* Create question groups with:

  * Group Name
  * Instructions
  * Marks
  * Starting Question Number
* Import existing Moodle XML question files
* Export questions to XML
* Generate formatted PDF question papers
* Embed original images into generated PDFs
* Validate questions before export
* Display question-type statistics
* Browse directories and open files directly from the application

## Supported Question Types

| Type | Description                                              |
| ---- | -------------------------------------------------------- |
| MCQ  | Multiple Choice Question with options and correct answer |
| SAQ  | Short Answer Question                                    |
| Long | Long/Essay-style Question                                |

## Tech Stack

* **Python 3**
* **Tkinter** – Graphical User Interface
* **Pillow** – Image processing and preview
* **ReportLab** – PDF generation
* **ElementTree** – XML parsing and generation
* **UUID** – Unique question identifiers
* **Regular Expressions** – Image tag processing

## Project Structure

```text
Moodle-Question-Editor/
│
├── main.py
├── README.md
└── requirements.txt
```

## Requirements

Make sure Python 3 is installed on your system.

Install the required external libraries:

```bash
pip install pillow reportlab
```

Tkinter is included with most standard Python installations.

### Linux

If Tkinter is not installed, you may need:

```bash
sudo apt install python3-tk
```

## How to Run

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git](https://github.com/Rajdeep-Bhukta/QGenXML--CEMK.git
```

Navigate to the project directory:

```bash
cd YOUR-REPOSITORY
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

## How to Use

### 1. Create a Question File

Click:

```text
New File (Save As...)
```

Choose a filename and location for the question file.

### 2. Add a Question

Select the question type and enter:

* Question text
* Marks
* MCQ options, if applicable
* Correct option index for MCQs

Click:

```text
Save/Add
```

### 3. Edit or Delete Questions

Select a question from the question list.

Use:

```text
Edit
```

to modify it or:

```text
Delete
```

to remove it.

### 4. Add Images

Use:

```text
Insert Image
```

to select an image and insert it into the current question.

Images are displayed in the preview and can also be embedded in the generated PDF.

### 5. Add Exam Header

Open:

```text
Header Details
```

You can provide:

* College
* Department
* Subject
* Subject Code
* Exam Name

### 6. Create Question Groups

Open:

```text
Question Group
```

and provide:

* Group name
* Instructions
* Marks
* Starting question number

The group information is displayed in the preview and included during export.

### 7. Validate Questions

Click:

```text
Verify
```

The application checks for common problems such as:

* Empty question text
* Invalid marks
* MCQs without options

### 8. Export

The application provides two export options:

```text
Export XML
Export PDF
```

XML export creates a structured XML file containing the question information.

PDF export generates a formatted question paper with exam information, questions, marks, MCQ options, groups, and embedded images.

## Image Handling

Images are referenced internally using tags such as:

```text
[IMG:image_name.png]
```

The application removes these tags from the visible question text and displays the actual image in the preview/PDF when the corresponding image file is available.

## Moodle XML

The application can read Moodle-style XML question files and convert supported Moodle question types into the application's internal format.

The supported mapping is:

```text
MCQ  → multichoice
SAQ  → shortanswer
Long → essay
```

## Validation

The built-in verification feature checks questions before export.

Examples of detected issues include:

```text
Q1: empty text
Q2: invalid marks
Q3: MCQ but no options
```

## Future Improvements

Possible future enhancements include:

* Direct Moodle API integration
* Drag-and-drop question reordering
* More Moodle question types
* Question bank/category management
* Search and filtering
* Custom PDF templates
* Automatic question numbering
* Better Moodle XML compatibility
* Dark/light theme support
* Undo/redo functionality
* Question duplication
* Export to additional formats

## Author

**RAJDEEP BHUKTA, LOKJIT RANA, ANIRBAN MAITI, SUVANKAR BHAKTA**



"ASSOCIATED WITH CEMK COLLEGE , UNDER THE SUPERVISED BY : DR. SUMAN BHOWMIK"

## License

This project is available for educational and personal use.

