import zipfile
import xml.etree.ElementTree as ET
import glob
import os
from collections import Counter, defaultdict

# Office Open XML Namespaces
REL_NS = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
W_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def audit_document_styles(directory_path):
    """
    Scans a directory for .docx files, identifies their attached templates, 
    and tallies the actual paragraph and character styles applied in the text.
    """
    template_tally = Counter()
    style_tally_by_template = defaultdict(Counter)
    global_style_tally = Counter()
    
    # Use glob to recursively find all docx files
    search_pattern = os.path.join(directory_path, '**', '*.docx')
    docx_files = glob.glob(search_pattern, recursive=True)
    
    print(f"Found {len(docx_files)} .docx files to analyze. Processing...")
    
    for docx_path in docx_files:
        try:
            with zipfile.ZipFile(docx_path, 'r') as docx_zip:
                attached_template = "Unknown_Or_Normal.dotm"
                
                # 1. Identify the Attached Template
                if 'word/_rels/settings.xml.rels' in docx_zip.namelist():
                    with docx_zip.open('word/_rels/settings.xml.rels') as rels_xml:
                        root = ET.parse(rels_xml).getroot()
                        for rel in root.findall('rel:Relationship', REL_NS):
                            if 'attachedTemplate' in rel.get('Type'):
                                attached_template = os.path.basename(rel.get('Target'))
                
                template_tally[attached_template] += 1
                
                # 2. Extract Applied Styles from the Document Body
                if 'word/document.xml' in docx_zip.namelist():
                    with docx_zip.open('word/document.xml') as doc_xml:
                        root = ET.parse(doc_xml).getroot()
                        
                        # Find all Paragraph styles (<w:pStyle>)
                        for pPr in root.iter(f"{{{W_NS['w']}}}pPr"):
                            pStyle = pPr.find(f"{{{W_NS['w']}}}pStyle")
                            if pStyle is not None:
                                style_val = pStyle.get(f"{{{W_NS['w']}}}val")
                                style_tally_by_template[attached_template][style_val] += 1
                                global_style_tally[style_val] += 1
                                
                        # Find all Character styles (<w:rStyle>)
                        for rPr in root.iter(f"{{{W_NS['w']}}}rPr"):
                            rStyle = rPr.find(f"{{{W_NS['w']}}}rStyle")
                            if rStyle is not None:
                                style_val = rStyle.get(f"{{{W_NS['w']}}}val")
                                style_tally_by_template[attached_template][style_val] += 1
                                global_style_tally[style_val] += 1
                                
        except zipfile.BadZipFile:
            print(f"Skipping corrupted archive: {os.path.basename(docx_path)}")
        except Exception as e:
            print(f"Error processing {os.path.basename(docx_path)}: {e}")
            
    return template_tally, style_tally_by_template, global_style_tally

def generate_report(directory_path):
    templates, template_styles, global_styles = audit_document_styles(directory_path)
    
    print("\n" + "="*50)
    print("TEMPLATE USAGE REPORT")
    print("="*50)
    for template, count in templates.most_common():
        print(f"- {template}: attached to {count} document(s)")
        
    print("\n" + "="*50)
    print("GLOBAL STYLE FREQUENCY (The 'Common Core')")
    print("="*50)
    # Filter out the extremely common 'Default' unstyled runs for cleaner data
    for style, count in global_styles.most_common(20):
        print(f"- {style}: applied {count} times")
        
    print("\n" + "="*50)
    print("TOP STYLES BY TEMPLATE")
    print("="*50)
    for template in templates:
        print(f"\n[{template}]")
        top_styles = template_styles[template].most_common(5)
        for style, count in top_styles:
            print(f"  - {style}: {count} uses")

if __name__ == "__main__":
    # Point this to your primary document repository
    target_directory = r"C:\Users\jwhow\Documents" 
    
    # If executing this from the new Ubuntu 24.03 environment, use the POSIX path:
    # target_directory = "/home/user/Documents"
    
    if os.path.exists(target_directory):
        generate_report(target_directory)
    else:
        print(f"Directory not found: {target_directory}")