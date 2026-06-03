"""
Utility script to view chunks created from processed PDFs
"""
import os
import json
import chromadb
from typing import Optional
import pandas as pd

def inspect_chunks(vector_db_path: str = "chroma_db", pdf_name: Optional[str] = None):
    """
    Inspect and display chunks stored in ChromaDB
    
    Args:
        vector_db_path: Path to chroma database
        pdf_name: Specific PDF to inspect (optional). If None, shows all.
    """
    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=vector_db_path)
        collection = client.get_or_create_collection(name="documents")
        
        # Get all data from collection
        all_data = collection.get()
        
        if not all_data or not all_data.get("ids"):
            print("❌ No chunks found in database")
            return
        
        # Filter by pdf_name if specified
        if pdf_name:
            filtered_ids = []
            filtered_docs = []
            filtered_metadata = []
            
            for id_, doc, metadata in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
                if metadata.get("pdf_name") == pdf_name:
                    filtered_ids.append(id_)
                    filtered_docs.append(doc)
                    filtered_metadata.append(metadata)
            
            if not filtered_ids:
                print(f"❌ No chunks found for PDF: {pdf_name}")
                return
            
            print(f"\n{'='*80}")
            print(f"📄 Chunks for PDF: {pdf_name}")
            print(f"{'='*80}\n")
            print(f"Total Chunks: {len(filtered_ids)}\n")
            
            for id_, doc, metadata in zip(filtered_ids, filtered_docs, filtered_metadata):
                chunk_id = metadata.get("chunk_id", "?")
                print(f"\n[Chunk {chunk_id}] (ID: {id_})")
                print(f"Content length: {len(doc)} characters")
                print(f"-" * 80)
                print(doc[:500] + "...\n" if len(doc) > 500 else doc + "\n")
                print()
        else:
            # Show all PDFs and their chunks summary
            pdfs = {}
            for id_, doc, metadata in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
                pdf = metadata.get("pdf_name", "Unknown")
                if pdf not in pdfs:
                    pdfs[pdf] = []
                pdfs[pdf].append({
                    "id": id_,
                    "chunk_id": metadata.get("chunk_id", "?"),
                    "content": doc,
                    "length": len(doc)
                })
            
            print(f"\n{'='*80}")
            print(f"📚 All Processed PDFs and Their Chunks")
            print(f"{'='*80}\n")
            
            for pdf_name, chunks in sorted(pdfs.items()):
                print(f"\n📄 {pdf_name}")
                print(f"   Total Chunks: {len(chunks)}")
                print(f"   Total Size: {sum(c['length'] for c in chunks):,} characters")
                print(f"   {'-' * 76}")
                for chunk in chunks:
                    content_preview = chunk['content'][:100].replace('\n', ' ')
                    print(f"   [Chunk {chunk['chunk_id']}] {len(chunk['content'])} chars | {content_preview}...")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def export_chunks_to_json(vector_db_path: str = "chroma_db", output_file: str = "chunks_export.json", pdf_name: Optional[str] = None):
    """
    Export chunks to a JSON file for analysis
    
    Args:
        vector_db_path: Path to chroma database
        output_file: Output JSON file path
        pdf_name: Specific PDF to export (optional)
    """
    try:
        client = chromadb.PersistentClient(path=vector_db_path)
        collection = client.get_or_create_collection(name="documents")
        
        all_data = collection.get()
        
        if not all_data or not all_data.get("ids"):
            print("❌ No chunks found in database")
            return
        
        export_data = {}
        
        for id_, doc, metadata in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
            pdf = metadata.get("pdf_name", "Unknown")
            
            if pdf_name and pdf != pdf_name:
                continue
            
            if pdf not in export_data:
                export_data[pdf] = []
            
            export_data[pdf].append({
                "chunk_id": metadata.get("chunk_id", 0),
                "content": doc,
                "length": len(doc)
            })
        
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        total_chunks = sum(len(chunks) for chunks in export_data.values())
        print(f"✅ Exported {total_chunks} chunks to {output_file}")
        print(f"   PDFs: {list(export_data.keys())}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def show_chunk_stats(vector_db_path: str = "chroma_db"):
    """Show statistics about all chunks"""
    try:
        client = chromadb.PersistentClient(path=vector_db_path)
        collection = client.get_or_create_collection(name="documents")
        
        all_data = collection.get()
        
        if not all_data or not all_data.get("ids"):
            print("❌ No chunks found in database")
            return
        
        stats = {}
        for metadata, doc in zip(all_data["metadatas"], all_data["documents"]):
            pdf = metadata.get("pdf_name", "Unknown")
            if pdf not in stats:
                stats[pdf] = {"count": 0, "total_chars": 0, "avg_chunk_size": 0}
            stats[pdf]["count"] += 1
            stats[pdf]["total_chars"] += len(doc)
        
        for pdf in stats:
            stats[pdf]["avg_chunk_size"] = stats[pdf]["total_chars"] / stats[pdf]["count"] if stats[pdf]["count"] > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"📊 Chunk Statistics")
        print(f"{'='*80}\n")
        
        df_data = []
        for pdf, stat in sorted(stats.items()):
            df_data.append({
                "PDF": pdf,
                "Chunks": stat["count"],
                "Total Characters": f"{stat['total_chars']:,}",
                "Avg Chunk Size": f"{stat['avg_chunk_size']:.0f}"
            })
        
        df = pd.DataFrame(df_data)
        print(df.to_string(index=False))
        print(f"\n{'='*80}\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    # Example usage:
    # python inspect_chunks.py                    # Show all PDFs and chunks summary
    # python inspect_chunks.py <pdf_name>         # Show detailed chunks for specific PDF
    # python inspect_chunks.py --stats            # Show statistics
    # python inspect_chunks.py --export            # Export to JSON
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--stats":
            show_chunk_stats()
        elif arg == "--export":
            export_chunks_to_json()
            print("\n✅ Chunks exported to chunks_export.json")
        else:
            # Treat as PDF name
            inspect_chunks(pdf_name=arg)
    else:
        # Show summary of all
        inspect_chunks()
