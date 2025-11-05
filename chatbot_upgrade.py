# chatbot_free_upgrade.py
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.prompts import PromptTemplate
#codebase
# For local LLM
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

class UBCCourseAssistant:
    def __init__(self, persist_directory='./chroma_db'):
        print("Loading stronger embeddings model...")
        # Free, stronger embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L12-v2",  # Free and high-quality
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        print("Loading vector store...")
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 10}  # get top 10 docs
        )

        print("Loading local LLM (Llama 2 7B)...")
        # Load Hugging Face Llama 2 7B (chat version)
        # Make sure you have downloaded the model locally or use HF cache
        model_name = "meta-llama/Llama-2-7b-chat-hf"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype="auto"
        )

        # Create a text-generation pipeline for chat
        self.llm_pipeline = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_length=512,
            temperature=0.3
        )

        # Prompt template
        template = """You are a helpful UBC Course Assistant chatbot. 
Use the following context about UBC courses to answer the question. 
If you don't know the answer, say so - don't make up information.
Always cite the course code when providing information.

Context: {context}

Question: {question}

Helpful Answer:"""

        self.prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        # Memory for conversation
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

        # Conversational Retrieval Chain
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm_pipeline,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": self.prompt}
        )

        print("✓ Free upgraded chatbot initialized successfully!")

    def _is_listing_query(self, question):
        keywords = ['all', 'list', 'show me', 'what are', 'which', 'available', 'courses in', 'tell me about']
        return any(word in question.lower() for word in keywords)

    def _extract_department(self, question):
        question_upper = question.upper()
        common_depts = ['CPSC', 'MATH', 'STAT', 'PHYS', 'CHEM', 'BIOL', 'ECON', 'COMM', 'ENGL', 'PSYC']
        for dept in common_depts:
            if dept in question_upper:
                return dept
        return None

    def _format_course_list(self, sources, dept=None):
        if not sources:
            return "I couldn't find any courses matching your query."
        courses_dict = {}
        for doc in sources:
            code = doc.metadata.get('course_code', 'Unknown')
            d = doc.metadata.get('department', 'Unknown')
            if dept and dept != d:
                continue
            if d not in courses_dict:
                courses_dict[d] = []
            courses_dict[d].append({
                'code': code,
                'content': doc.page_content
            })

        response_parts = []
        if dept:
            response_parts.append(f"Here are {dept} courses:\n")
        else:
            response_parts.append("Here are the courses I found:\n")

        for d, courses in courses_dict.items():
            if len(courses_dict) > 1:
                response_parts.append(f"\n**{d} Courses:**")
            for i, course in enumerate(courses[:15], 1):
                lines = course['content'].split('\n')
                desc = ""
                for line in lines:
                    if line.startswith("Description:"):
                        desc = line.replace("Description:", "").strip()
                        break
                if desc and len(desc) > 150:
                    desc = desc[:150] + "..."
                response_parts.append(f"\n{i}. **{course['code']}**: {desc}" if desc else f"\n{i}. **{course['code']}**")

        if len(sources) > 15:
            response_parts.append(f"\n\n*Showing top 15 of {len(sources)} results.*")
        return ''.join(response_parts)

    def ask(self, question):
        # Retrieve docs
        try:
            sources = self.retriever.get_relevant_documents(question)
        except:
            sources = []

        is_listing = self._is_listing_query(question)
        dept = self._extract_department(question)

        if not is_listing:
            try:
                result = self.chain({"question": question})
                answer = result['answer']
                sources = result['source_documents']
            except:
                is_listing = True

        if is_listing:
            answer = self._format_course_list(sources, dept)

        return {'answer': answer, 'sources': sources}

    def reset_conversation(self):
        self.memory.clear()

# Test
if __name__ == "__main__":
    assistant = UBCCourseAssistant()
    questions = [
        "What is CPSC 110 about?",
        "List all CPSC courses",
        "Tell me about MATH 100",
        "Show me computer science courses"
    ]
    for q in questions:
        print("\n" + "="*60)
        print(f"Q: {q}")
        print("="*60)
        result = assistant.ask(q)
        print(result['answer'])
        print(f"\n[Found {len(result['sources'])} sources]")
