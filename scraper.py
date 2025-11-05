import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re


class UBCCourseScraper:
    def __init__(self):
        self.base_url = "https://vancouver.calendar.ubc.ca/course-descriptions/subject"
        self.courses = []

    def scrape_courses_by_subject(self, subject_code):
        """Scrape courses for a specific subject from UBC Calendar"""
        # UBC Calendar uses lowercase subject codes with 'v' suffix
        url = f"{self.base_url}/{subject_code.lower()}v"

        try:
            print(f"  Fetching {url}...")
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                print(f"  ✗ Failed: HTTP {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            courses = []

            # Find all course entries - they're usually in <dt> tags or divs
            # Pattern: "CPSC 110 (4) Course Title"
            text_content = soup.get_text()

            # Use regex to find course codes and descriptions
            # Enhanced pattern matching for course codes
            pattern = rf'{subject_code.upper()}_V\s*\d{{3}}(?:\s*\(\d+(?:\/\d+)?\))?\s*[A-Za-z]+'
            course_matches = re.finditer(pattern, text_content)

            positions = [match.start() for match in course_matches]

            # Extract prerequisites and additional info
            prereq_pattern = r'(?:Prerequisites?|Pre-reqs?):?\s*([^.]*\.)'
            coreq_pattern = r'(?:Corequisites?|Co-reqs?):?\s*([^.]*\.)'

            for i, start_pos in enumerate(positions):
                try:
                    # Get text from this course to the next (or end)
                    end_pos = positions[i + 1] if i + 1 < len(positions) else start_pos + 500
                    course_text = text_content[start_pos:end_pos].strip()

                    # Extract course code (e.g., "CPSC_V 110")
                    course_code_match = re.match(rf'({subject_code.upper()}_V \d{{3}})', course_text)
                    if not course_code_match:
                        continue

                    course_code = course_code_match.group(1).replace('_V', '')

                    # Extract description (everything after the credits marker)
                    # Look for pattern: (credits) Description
                    # Enhanced description extraction
                    desc_match = re.search(
                        r'\(\d+(?:\/\d+)?\)\s*(.+?)(?=(?:Prerequisites?:|Corequisites?:|Pre-reqs?:|Co-reqs?:|Equivalency:|This course|Credits:|$))',
                        course_text, 
                        re.DOTALL | re.IGNORECASE
                    )

                    if desc_match:
                        description = desc_match.group(1).strip()
                        # Better description cleaning
                        description = re.sub(r'\s+', ' ', description)
                        description = re.sub(r'\[[\w\s]+\]', '', description)
                        description = re.sub(r'\([Ff]ormerly[^)]+\)', '', description)
                        
                        # Extract prerequisites
                        prereqs = ""
                        prereq_match = re.search(prereq_pattern, course_text, re.IGNORECASE)
                        if prereq_match:
                            prereqs = prereq_match.group(1).strip()

                        if description and len(description) > 20:
                            courses.append({
                                'department': subject_code.upper(),
                                'course_code': course_code,
                                'description': description,
                                'prerequisites': prereqs,
                                'campus': 'UBCV',
                                'year': '2024',
                                'session': 'W'
                            })

                except Exception as e:
                    continue

            return courses

        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout")
            return []
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return []

    def save_to_json(self, filename='data/raw/ubc_courses.json'):
        """Save scraped data to JSON"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.courses, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved {len(self.courses)} courses to {filename}")


# Run the scraper
if __name__ == "__main__":
    scraper = UBCCourseScraper()

    # Comprehensive list of UBC subjects (most popular ones)
    subjects = [
        # Computer Science & Engineering
        'APSC', 'BMEG', 'CPEN', 'CPSC', 'ELEC', 'MECH', 'CIVL', 'CHBE', 'EECE', 'EOSC',

        # Mathematics & Statistics
        'MATH', 'STAT', 'AMAT',

        # Sciences
        'PHYS', 'CHEM', 'BIOL', 'MICB', 'BIOC', 'ASTR', 'ATSC', 'GEOB', 'GEOG',

        # Business & Economics
        'COMM', 'ECON', 'BUSI', 'BAAC', 'BABS', 'BAFI', 'BAIT', 'BAMA', 'BAMS',

        # Arts & Humanities
        'ENGL', 'HIST', 'PHIL', 'PSYC', 'SOCI', 'ANTH', 'ASIA', 'CLST', 'FREN',
        'GERM', 'SPAN', 'LING', 'MUSC', 'THTR', 'VISA', 'CRWR',

        # Social Sciences
        'POLI', 'GEOG', 'GRSJ', 'WRDS', 'SCIE', 'ASTU',

        # Life Sciences
        'BIOL', 'CAPS', 'FNH', 'FOOD', 'FRST', 'LFS', 'PLAN', 'NURS',

        # Others
        'KIN', 'EDUC', 'LAW', 'MEDI', 'DENT', 'PHAR'
    ]

    print(f"🚀 Starting to scrape {len(subjects)} subjects from UBC Calendar...")
    print("=" * 60)

    all_courses = []
    successful = 0
    failed = 0

    for i, subject in enumerate(subjects, 1):
        print(f"\n[{i}/{len(subjects)}] {subject}:")
        courses = scraper.scrape_courses_by_subject(subject)

        if courses:
            all_courses.extend(courses)
            successful += 1
            print(f"  ✓ Found {len(courses)} courses")
        else:
            failed += 1

        # Be respectful to the server
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"✓ Successfully scraped: {successful} subjects")
    print(f"✗ Failed: {failed} subjects")
    print(f"📚 Total courses: {len(all_courses)}")

    scraper.courses = all_courses
    scraper.save_to_json()

    if len(all_courses) > 0:
        print("\n🎉 Success! Now run: python create_vectordb.py")
    else:
        print("\n⚠️  No courses found. Check your internet connection.")