import json
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re


class UBCCourseAssistant:
    def __init__(self, persist_directory='./chroma_db'):
        """Initialize with ChromaDB"""
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.embedding_function = SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-MiniLM-L3-v2"
            )
            self.collection = self.client.get_collection(
                name="courses",
                embedding_function=self.embedding_function
            )
            print("✓ Vector store loaded successfully")
        except Exception as e:
            print(f"Error initializing vector store: {e}")
            raise

        # Load courses for direct access
        try:
            with open('data/raw/ubc_courses.json', 'r', encoding='utf-8') as f:
                self.courses = json.load(f)
            print(f"Loaded {len(self.courses)} courses")
        except Exception as e:
            print(f"Warning: Could not load courses: {e}")
            self.courses = []

        # Index courses by department
        self.dept_courses = {}
        for course in self.courses:
            dept = course['department']
            if dept not in self.dept_courses:
                self.dept_courses[dept] = []
            self.dept_courses[dept].append(course)

        print("✓ Chatbot initialized successfully!")

    def _get_all_courses_by_department(self, dept_code):
        """Get filtered courses for a department"""
        try:
            if dept_code in self.dept_courses:
                courses = self.dept_courses[dept_code]
                filtered_courses = []
                
                # Group by level for better organization
                by_level = {}
                for course in courses:
                    level = course['course_code'][-3]
                    if level not in by_level:
                        by_level[level] = []
                    by_level[level].append(course)

                # Select representative courses from each level
                for level, level_courses in sorted(by_level.items()):
                    # Take first 5 courses from each level
                    selected = sorted(level_courses, key=lambda x: x['course_code'])[:5]
                    
                    for course in selected:
                        filtered_courses.append({
                            'code': course['course_code'],
                            'department': course['department'],
                            'content': (
                                f"{course['course_code']} - {course['department']} Course\n"
                                f"Description: {course['description']}\n"
                                f"Prerequisites: {course.get('prerequisites', '')}\n"
                                f"Department: {course['department']}"
                            ),
                            'level': level
                        })

                print(f"Selected {len(filtered_courses)} courses for {dept_code}")
                return filtered_courses

            return []
        except Exception as e:
            print(f"Error getting courses: {e}")
            return []

    def _extract_department_code(self, question):
        """Extract department code from question"""
        question_upper = question.upper()

        # Common department codes
        common_depts = [
            'CPSC', 'MATH', 'STAT', 'PHYS', 'CHEM', 'BIOL', 'ECON', 'COMM',
            'ENGL', 'PSYC', 'HIST', 'PHIL', 'GEOG', 'POLI', 'SOCI', 'KIN',
            'MECH', 'ELEC', 'CIVL', 'CPEN', 'APSC', 'FRST', 'FOOD', 'FNH'
        ]

        for dept in common_depts:
            if dept in question_upper:
                return dept

        # Try to match patterns like "computer science"
        subject_map = {
            'computer science': 'CPSC',
            'mathematics': 'MATH',
            'math': 'MATH',
            'statistics': 'STAT',
            'physics': 'PHYS',
            'chemistry': 'CHEM',
            'biology': 'BIOL',
            'economics': 'ECON',
            'commerce': 'COMM',
            'business': 'COMM',
            'english': 'ENGL',
            'psychology': 'PSYC',
            'history': 'HIST',
        }

        for subject, code in subject_map.items():
            if subject in question.lower():
                return code

        return None

    def _extract_course_number(self, question):
        """Extract specific course number like '110' from 'CPSC 110'"""
        # Match patterns like "CPSC 110", "cpsc110", "CPSC-110"
        match = re.search(r'[A-Z]{4}\s*[-]?\s*(\d{3})', question.upper())
        if match:
            return match.group(0).replace('-', ' ').replace('  ', ' ')
        return None

    def _is_listing_query(self, question):
        """Check if user wants a list of courses"""
        listing_keywords = [
            'all', 'list', 'show me', 'what are', 'which', 'available',
            'courses in', 'tell me about', 'what courses', 'give me'
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in listing_keywords)

    def _search_by_semantic(self, question, k=10):
        """Semantic search using ChromaDB"""
        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=k
            )
            
            courses = []
            if results and results['documents']:
                for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                    courses.append({
                        'code': metadata.get('course_code', 'Unknown'),
                        'department': metadata.get('department', 'Unknown'),
                        'content': doc
                    })
            return courses
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []

    def _format_course_list(self, courses, dept=None, max_display=15):
        """Improved course list formatting without LLM"""
        if not courses:
            return f"I couldn't find any {dept if dept else ''} courses."

        sections = []
        
        # Introduction
        if dept:
            sections.append(f"# Key {dept} Courses\n")
        else:
            sections.append("# Course Overview\n")

        # Group by level and type
        level_groups = {}
        for course in courses[:max_display]:
            level = course['code'][-3] if len(course['code']) >= 3 else '0'
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(course)

        # Format each level
        for level in sorted(level_groups.keys()):
            courses = level_groups[level]
            if not courses:
                continue

            sections.append(f"\n## {level}00-Level Courses\n")
            
            # Sort courses by number
            courses.sort(key=lambda x: int(x['code'].split()[-1]))
            
            for course in courses:
                desc = ""
                prereqs = ""
                for line in course['content'].split('\n'):
                    if 'Description:' in line:
                        desc = line.split('Description:', 1)[1].strip()
                    elif 'Prerequisites:' in line:
                        prereqs = line.split('Prerequisites:', 1)[1].strip()

                # Format course info
                course_section = [f"\n### {course['code']}"]
                
                if desc:
                    # Truncate long descriptions
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    course_section.append(desc)
                
                if prereqs:
                    course_section.append(f"\n**Prerequisites:** {prereqs}")
                
                course_section.append("\n---")
                sections.append('\n'.join(course_section))

        return '\n'.join(sections)

    def _format_single_course(self, course):
        """Enhanced course formatting"""
        content = course['content']
        lines = content.split('\n')
        
        # Extract key information
        description = ""
        prerequisites = ""
        
        for line in lines:
            if 'Description:' in line:
                description = line.split('Description:', 1)[1].strip()
            elif 'Prerequisites:' in line:
                prerequisites = line.split('Prerequisites:', 1)[1].strip()

        response = f"""**{course['code']}**

📚 **Department:** {course['department']}

📝 **Description:**
{description}"""

        if prerequisites:
            response += f"\n\n🔑 **Prerequisites:**\n{prerequisites}"

        return response

    def ask(self, question):
        """Enhanced ask method with better error handling"""
        try:
            # Extract department and course number
            dept = self._extract_department_code(question)
            course_num = self._extract_course_number(question)
            is_listing = self._is_listing_query(question)

            # Strategy 1: Department listing (most reliable)
            if is_listing and dept:
                courses = self._get_all_courses_by_department(dept)
                if courses:
                    answer = self._format_course_list(courses, dept)
                    return {'answer': answer, 'sources': courses[:10]}

            # Strategy 2: Specific course query (e.g., "What is CPSC 110?")
            if course_num and not is_listing:
                courses = self._search_by_semantic(course_num, k=3)
                if courses:
                    # Return the most relevant match
                    answer = self._format_single_course(courses[0])
                    return {'answer': answer, 'sources': courses}
                else:
                    return {
                        'answer': f"I couldn't find information about {course_num}.",
                        'sources': []
                    }

            # Strategy 3: Topic-based search (e.g., "machine learning courses")
            if is_listing or 'course' in question.lower():
                courses = self._search_by_semantic(question, k=15)
                answer = self._format_course_list(courses, dept, max_display=15)
                return {'answer': answer, 'sources': courses}

            # Strategy 4: General question - semantic search
            courses = self._search_by_semantic(question, k=5)
            if courses:
                # For general questions, show the most relevant course
                answer = self._format_single_course(courses[0])
                return {'answer': answer, 'sources': courses}
            else:
                return {
                    'answer': "I couldn't find relevant information. Try asking about specific courses or departments.",
                    'sources': []
                }

        except Exception as e:
            print(f"Error processing question: {e}")
            return {
                'answer': "I encountered an error. Please try asking in a different way.",
                'sources': []
            }

    def reset_conversation(self):
        """Clear conversation history"""
        pass


# Test the chatbot
if __name__ == "__main__":
    print("Initializing UBC Course Assistant...")
    assistant = UBCCourseAssistant()

    # Test questions
    test_questions = [
        "What is CPSC 110 about?",
        "Give me all CPSC courses",
        "List all MATH courses",
        "What are machine learning courses?",
        "Tell me about MATH 100",
        "Show me computer science courses"
    ]

    for q in test_questions:
        print(f"\n{'=' * 70}")
        print(f"Q: {q}")
        print('=' * 70)
        result = assistant.ask(q)
        print(result['answer'])
        print(f"\n[Retrieved {len(result['sources'])} sources]")
        input("\nPress Enter for next question...")