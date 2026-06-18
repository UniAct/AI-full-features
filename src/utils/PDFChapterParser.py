import fitz
import json
import logging

logger = logging.getLogger(__name__)

class PDFChapterParser:
    @staticmethod
    def extract_chapters(file_path: str, llm_provider=None) -> list:
        """
        Main entry point for extracting chapters from a PDF.
        """
        try:
            doc = fitz.open(file_path)
            num_pages = len(doc)
            
            # FR-002: Bypass logic for short documents
            if num_pages <= 20:
                print("Document is 20 pages or less. Bypassing chapter splitting.")
                return [{"title": "Document", "start_page": 1, "end_page": num_pages}]
            
            # FR-003: Try extracting TOC first
            toc = doc.get_toc()
            if toc:
                chapters = PDFChapterParser._parse_toc(toc, num_pages)
                if chapters:
                    return chapters
                    
            # FR-005: Fallback to LLM heuristic
            if llm_provider:
                print("No TOC found. Falling back to LLM heuristic splitting.")
                return PDFChapterParser._extract_llm_heuristic_chapters(doc, num_pages, llm_provider)
                
            return [{"title": "Document", "start_page": 1, "end_page": num_pages}]
        except Exception as e:
            logger.error(f"Error parsing PDF chapters: {e}")
            return [{"title": "Document", "start_page": 1, "end_page": 1}]

    @staticmethod
    def _parse_toc(toc: list, num_pages: int) -> list:
        if not toc:
            return []
            
        # Find the top-most level in the TOC
        min_level = min(item[0] for item in toc)
        
        # Filter for only the top-level chapters
        top_level_toc = [item for item in toc if item[0] == min_level]
        
        chapters = []
        for i in range(len(top_level_toc)):
            level, title, page = top_level_toc[i]
            
            end_page = num_pages
            if i + 1 < len(top_level_toc):
                end_page = top_level_toc[i+1][2] - 1
                if end_page < page:
                    end_page = page
            
            chapters.append({
                "title": title.strip(),
                "start_page": page,
                "end_page": end_page
            })
            
        # Filter out common front/back matter
        ignore_terms = {
            "cover", "copyright", "table of contents", "contents", 
            "preface", "index", "about the author", "about the authors", 
            "acknowledgments", "acknowledgement", "acknowledgements", "dedication", 
            "title page", "colophon", "bibliography", "references"
        }
        
        filtered_chapters = []
        for c in chapters:
            if c["start_page"] > c["end_page"]:
                continue
            
            title_lower = c["title"].lower().strip()
            
            # Exact match for common non-content pages or empty titles
            if title_lower in ignore_terms or not title_lower:
                continue
                
            filtered_chapters.append(c)
            
        return filtered_chapters

    @staticmethod
    def _extract_llm_heuristic_chapters(doc, num_pages: int, llm_provider) -> list:
        skeleton = ""
        for i in range(num_pages):
            page = doc.load_page(i)
            text = page.get_text("text").strip()
            if not text:
                continue
            
            if len(text) > 500:
                sample = text[:250] + "\n...\n" + text[-250:]
            else:
                sample = text
            
            skeleton += f"\n--- Page {i+1} ---\n{sample}\n"
        
        prompt = (
            "You are an expert document structure analyzer. "
            "I am providing you with a skeletal representation of a document containing only the "
            "headers, footers, and first/last paragraphs of each page.\n"
            "Your task is to identify logical chapter boundaries based on this structure.\n\n"
            "Return ONLY a valid JSON array of objects representing the chapters. "
            "Each object must have the following keys: 'title' (string), 'start_page' (integer), and 'end_page' (integer).\n"
            "Do not include any markdown formatting, code blocks, or explanatory text. Just the raw JSON array.\n\n"
            f"Document Skeleton:\n{skeleton}"
        )
        
        response = llm_provider.generate_text(prompt=prompt, max_output_tokens=2000)
        if not response:
            return []
            
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
                
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Error parsing LLM chapters JSON: {e}")
            return []
