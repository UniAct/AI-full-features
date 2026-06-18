from string import Template

#### RAG PROMPTS ####

#### System ####

system_prompt = Template("\n".join([
    "You are an assistant to generate a response for the user.",
    "You will be provided with a set of documents associated with the user's query.",
    "You have to generate a response based on the documents provided.",
    "Ignore the documents that are not relevant to the user's query.",
    "If the answer to the user's question cannot be found within the provided documents, you MUST explicitly tell the user that the answer is not in the specific content they chose.",
    "Do NOT make up answers or use outside knowledge.",
    "You have to generate response in the same language as the user's query.",
    "Be polite and respectful to the user.",
    "Be precise and concise in your response. Avoid unnecessary information.",
]))

#### Document ####
document_prompt = Template(
    "\n".join([
        "## Document No: $doc_num",
        "### Content: $chunk_text",
    ])
)

#### Footer ####
footer_prompt = Template("\n".join([
    "Based only on the above documents, please generate an answer for the user.",
    "## Question:",
    "$query",
    "", # tell me that query ended
    "## Answer:",
]))

exam_prompt = Template("\n".join([
    "Using only the above documents, generate an exam focused on the requested content.",
    "Analyze the provided documents to generate a high-quality, thought-provoking exam.",
    "If the Query is empty or generic, base the exam on the core themes, concepts, and narrative details present in the documents.",
    "If the Query specifies a topic, focus the exam on that specific topic.",
    "CRITICAL RULES FOR QUESTIONS:",
    "1. You MUST generate EXACTLY $mcq_count multiple-choice questions and EXACTLY $written_count written questions. Do not generate more or less.",
    "2. Questions must sound natural, analytical, and human-made. They should require critical thinking.",
    "3. NEVER use phrases like 'Based on the provided documents' or 'According to the text'.",
    "4. Assume the context of the material is the real world of the exam.",
    "5. Do not invent facts outside the provided text.",
    "The exam must be returned as valid JSON with the following keys:",
    "file_id, chapters, difficulty, $json_keys",
    "$mcq_instructions",
    "$written_instructions",
    "Do not invent answers outside the provided documents.",
    "If the exam content cannot be drawn from the documents, explicitly indicate that in the answer fields.",
    "Use the request parameters:",
    "- Query: $query",
    "- Difficulty: $difficulty",
    "- MCQ count: EXACTLY $mcq_count",
    "- Written question count: EXACTLY $written_count",
    "- File ID: $file_id",
    "- Chapters: $chapters",
    "Output only valid JSON without markdown formatting. The output MUST be a JSON object containing the required arrays.",
]))