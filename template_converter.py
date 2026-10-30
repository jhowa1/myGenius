import zipfile
import xml.etree.ElementTree as ET
import subprocess
import time
import os
import sys

# PyUNO imports (These will only work when run via LibreOffice's Python environment)
try:
    import uno
    from com.sun.star.beans import PropertyValue
except ImportError:
    print("Error: This script must be executed using LibreOffice's bundled python.")
    sys.exit(1)

# Word XML Namespaces
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def extract_styles_from_dotx(dotx_path):
    """Extracts style names, fonts, and sizes from the Word template XML."""
    styles_data = {}
    
    with zipfile.ZipFile(dotx_path, 'r') as docx_zip:
        with docx_zip.open('word/styles.xml') as styles_xml:
            tree = ET.parse(styles_xml)
            root = tree.getroot()

            # Iterate through all styles defined in the template
            for style in root.findall('w:style', NS):
                if style.get(f"{{{NS['w']}}}type") != 'paragraph':
                    continue
                
                style_name = style.find('w:name', NS)
                if style_name is None:
                    continue
                
                name = style_name.get(f"{{{NS['w']}}}val")
                
                # Extract Run Properties (rPr) for font definitions
                rPr = style.find('w:rPr', NS)
                if rPr is not None:
                    font_node = rPr.find('w:rFonts', NS)
                    size_node = rPr.find('w:sz', NS)
                    
                    font_name = font_node.get(f"{{{NS['w']}}}ascii") if font_node is not None else None
                    # Word stores font sizes in half-points (e.g., 24 = 12pt)
                    font_size = int(size_node.get(f"{{{NS['w']}}}val")) / 2 if size_node is not None else None
                    
                    if font_name or font_size:
                        styles_data[name] = {'font': font_name, 'size': font_size}
                        
    return styles_data

def launch_libreoffice_listener(soffice_path):
    """Starts LibreOffice in headless listening mode."""
    cmd = [
        soffice_path,
        "--headless",
        "--invisible",
        "--nocrashreport",
        "--nodefault",
        "--nofirststartwizard",
        "--nologo",
        "--norestore",
        '--accept=socket,host=localhost,port=2002;urp;StarOffice.ServiceManager'
    ]
    process = subprocess.Popen(cmd)
    time.sleep(3) # Wait for the socket to open
    return process

def create_ott_template(parsed_styles, output_ott_path):
    """Connects to UNO, creates a document, applies styles, and saves as .ott."""
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    
    # Open a blank writer document
    doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
    style_families = doc.StyleFamilies
    para_styles = style_families.getByName("ParagraphStyles")
    
    # Map Word style names (keys) to native LibreOffice style names (values)
    style_mapping = {
        "Normal": "Standard",
        "NoSpacing": "Text body",         # LO uses 'Text body' for standard non-spaced paragraphs
        "BodyText": "Text body",          # Consolidating Word's redundant body styles
        "ListParagraph": "List 1",        # Maps to LO's default bullet/indent structural style
        "Hyperlink": "Internet link",     # Native LO character style for URLs
        "Hyperlink-xref": "Internet link",
        "Heading1": "Heading 1",
        "Heading2": "Heading 2",
        "Heading3": "Heading 3",
        "Code": "Preformatted Text",      # Best LO default for monospaced code blocks
        "CodeExample": "Preformatted Text",
        "TOC1": "Contents 1",             # LO's native Table of Contents mapping
        "TOC2": "Contents 2",
        "TOC3": "Contents 3",
        "TableParagraph": "Table Contents",
        "ListBullet": "List 1 Start",     
        "ListNumber": "Numbering 1 Start",
        "Caption": "Caption",
        "Strong": "Strong Emphasis"       # Native LO character style for bolding
    }


    for word_style, attributes in parsed_styles.items():
        lo_style_name = style_mapping.get(word_style, word_style)
        
        if para_styles.hasByName(lo_style_name):
            style_obj = para_styles.getByName(lo_style_name)
            if attributes.get('font'):
                style_obj.CharFontName = attributes['font']
            if attributes.get('size'):
                style_obj.CharHeight = float(attributes['size'])

    # Prepare save properties
    save_props = (
        PropertyValue(Name="FilterName", Value="writer8_template"), # .ott format
        PropertyValue(Name="Overwrite", Value=True)
    )
    
    # Convert local path to UNO URL
    file_url = uno.systemPathToFileUrl(os.path.abspath(output_ott_path))
    doc.storeAsURL(file_url, save_props)
    doc.close(True)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python template_converter.py <soffice_binary_path> <input.dotx> <output.ott>")
        sys.exit(1)

    soffice_path = sys.argv[1]
    input_dotx = sys.argv[2]
    output_ott = sys.argv[3]

    print(f"Extracting styles from {input_dotx}...")
    styles = extract_styles_from_dotx(input_dotx)
    
    print("Launching LibreOffice in listening mode...")
    lo_process = launch_libreoffice_listener(soffice_path)
    
    try:
        print("Connecting via UNO and generating .ott...")
        create_ott_template(styles, output_ott)
        print(f"Successfully created: {output_ott}")
    finally:
        lo_process.terminate()