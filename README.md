# UBC Course Assistant

A smart chatbot that helps students find and learn about UBC courses using vector search and natural language processing.

## Features

- Search for specific courses (e.g., "What is CPSC 110 about?")
- List courses by department (e.g., "Show me all MATH courses")
- Find courses by topic (e.g., "What machine learning courses are available?")
- Get detailed course information including prerequisites
- Smart semantic search for course discovery

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ubc-course-assistant.git
cd ubc-course-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

```python
from chatbot import UBCCourseAssistant

# Initialize the assistant
assistant = UBCCourseAssistant()

# Ask questions
response = assistant.ask("What is CPSC 110 about?")
print(response['answer'])
```

## Project Structure

```
ubc-course-assistant/
├── chatbot.py         # Main chatbot implementation
├── data/             # Course data directory
│   └── raw/          # Raw course data
├── chroma_db/        # Vector database storage
└── requirements.txt  # Python dependencies
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
