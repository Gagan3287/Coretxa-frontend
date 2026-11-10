import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Ellipse, ArrowStyle

def create_system_architecture():
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Background
    fig.patch.set_facecolor('#ffffff')

    # Title
    ax.text(6, 9.6, 'Figure 5.1: CORTEXA System Architecture Diagram', 
            fontsize=14, fontweight='bold', ha='center', va='center', fontfamily='serif')

    # Tier 1: Client Tier
    rect1 = FancyBboxPatch((0.5, 7.0), 11, 1.8, boxstyle="round,pad=0.2", fc="#f0fdf4", ec="#16a34a", lw=1.5)
    ax.add_patch(rect1)
    ax.text(0.8, 8.5, '1. CLIENT PRESENTATION TIER', fontsize=11, fontweight='bold', color="#15803d", fontfamily='serif')
    
    # Client Sub-boxes
    b1 = FancyBboxPatch((1.0, 7.2), 4.5, 1.1, boxstyle="round,pad=0.1", fc="#ffffff", ec="#86efac", lw=1.2)
    ax.add_patch(b1)
    ax.text(3.25, 7.9, 'Next.js 16 Web Application\n(React 19, Tailwind CSS, Vercel Edge)', 
            fontsize=9, ha='center', va='center', fontfamily='sans-serif')

    b2 = FancyBboxPatch((6.5, 7.2), 4.5, 1.1, boxstyle="round,pad=0.1", fc="#ffffff", ec="#86efac", lw=1.2)
    ax.add_patch(b2)
    ax.text(8.75, 7.9, 'Electron Desktop Application (.exe)\n(Native Windows Frame, NSIS Installer)', 
            fontsize=9, ha='center', va='center', fontfamily='sans-serif')

    # Tier 2: API Gateway & Application Server
    rect2 = FancyBboxPatch((0.5, 4.7), 11, 1.8, boxstyle="round,pad=0.2", fc="#eff6ff", ec="#2563eb", lw=1.5)
    ax.add_patch(rect2)
    ax.text(0.8, 6.2, '2. API GATEWAY & APPLICATION SERVER TIER (FastAPI / Render Cloud)', 
            fontsize=11, fontweight='bold', color="#1d4ed8", fontfamily='serif')

    b3 = FancyBboxPatch((1.0, 4.9), 3.2, 1.1, boxstyle="round,pad=0.1", fc="#ffffff", ec="#93c5fd", lw=1.2)
    ax.add_patch(b3)
    ax.text(2.6, 5.45, 'Auth & RLS Middleware\nTenant Isolation (JWT)', fontsize=9, ha='center', va='center')

    b4 = FancyBboxPatch((4.5, 4.9), 3.2, 1.1, boxstyle="round,pad=0.1", fc="#ffffff", ec="#93c5fd", lw=1.2)
    ax.add_patch(b4)
    ax.text(6.1, 5.45, 'REST Endpoints\n/api/v1/chat, /ingest', fontsize=9, ha='center', va='center')

    b5 = FancyBboxPatch((8.0, 4.9), 3.2, 1.1, boxstyle="round,pad=0.1", fc="#ffffff", ec="#93c5fd", lw=1.2)
    ax.add_patch(b5)
    ax.text(9.6, 5.45, 'Direct Release Route\n/api/download (Edge Redirect)', fontsize=9, ha='center', va='center')

    # Tier 3: Async Queue & Processing Tier
    rect3 = FancyBboxPatch((0.5, 2.5), 11, 1.7, boxstyle="round,pad=0.2", fc="#faf5ff", ec="#9333ea", lw=1.5)
    ax.add_patch(rect3)
    ax.text(0.8, 3.9, '3. ASYNCHRONOUS TASK QUEUE & INGESTION WORKER', 
            fontsize=11, fontweight='bold', color="#7e22ce", fontfamily='serif')

    b6 = FancyBboxPatch((1.5, 2.7), 4.0, 1.0, boxstyle="round,pad=0.1", fc="#ffffff", ec="#d8b4fe", lw=1.2)
    ax.add_patch(b6)
    ax.text(3.5, 3.2, 'Upstash Redis Event Stream\n(cortexa:ingestion:stream)', fontsize=9, ha='center', va='center')

    b7 = FancyBboxPatch((6.5, 2.7), 4.0, 1.0, boxstyle="round,pad=0.1", fc="#ffffff", ec="#d8b4fe", lw=1.2)
    ax.add_patch(b7)
    ax.text(8.5, 3.2, 'Background Ingestion Worker\n(PyPDF parser, Text Sanitizer)', fontsize=9, ha='center', va='center')

    # Tier 4: Storage & AI Tier
    rect4 = FancyBboxPatch((0.5, 0.3), 11, 1.7, boxstyle="round,pad=0.2", fc="#fff7ed", ec="#ea580c", lw=1.5)
    ax.add_patch(rect4)
    ax.text(0.8, 1.7, '4. AI INTELLIGENCE & MULTI-TENANT STORAGE TIER', 
            fontsize=11, fontweight='bold', color="#c2410c", fontfamily='serif')

    b8 = FancyBboxPatch((1.2, 0.5), 4.5, 1.0, boxstyle="round,pad=0.1", fc="#ffffff", ec="#fdba74", lw=1.2)
    ax.add_patch(b8)
    ax.text(3.45, 1.0, 'Google Gemini AI Engine\ngemini-embedding-001 (768-d) & Flash LLM', fontsize=9, ha='center', va='center')

    b9 = FancyBboxPatch((6.3, 0.5), 4.5, 1.0, boxstyle="round,pad=0.1", fc="#ffffff", ec="#fdba74", lw=1.2)
    ax.add_patch(b9)
    ax.text(8.55, 1.0, 'Supabase PostgreSQL + pgvector\nRow-Level Security (RLS) Tenant Scoped', fontsize=9, ha='center', va='center')

    # Inter-tier Connecting Arrows
    arrow_style = dict(facecolor='#475569', edgecolor='#475569', width=1.5, headwidth=6)
    ax.annotate('', xy=(6.0, 6.5), xytext=(6.0, 7.0), arrowprops=dict(arrowstyle="<->", color="#475569", lw=1.8))
    ax.annotate('', xy=(6.0, 4.2), xytext=(6.0, 4.7), arrowprops=dict(arrowstyle="<->", color="#475569", lw=1.8))
    ax.annotate('', xy=(6.0, 2.0), xytext=(6.0, 2.5), arrowprops=dict(arrowstyle="<->", color="#475569", lw=1.8))

    plt.tight_layout()
    plt.savefig('e:/cortexa-frontend/cortexa/docs/diagrams/system_architecture.png', dpi=300)
    plt.close()
    print('Generated system_architecture.png')

def create_use_case_diagram():
    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 9.5)
    ax.axis('off')

    # Title
    ax.text(5.5, 9.1, 'Figure 5.2: CORTEXA Use Case Diagram', 
            fontsize=14, fontweight='bold', ha='center', va='center', fontfamily='serif')

    # System boundary box
    sys_box = FancyBboxPatch((2.6, 0.5), 5.8, 8.2, boxstyle="round,pad=0.2", fc="#f8fafc", ec="#64748b", lw=2, linestyle='--')
    ax.add_patch(sys_box)
    ax.text(5.5, 8.4, 'Cortexa AI Platform Boundary', fontsize=12, fontweight='bold', color='#1e293b', ha='center')

    # Actors
    # Actor 1: End User / Tenant
    ax.plot([1.2, 1.2], [5.6, 6.3], color="#0f172a", lw=2) # body
    circle1 = plt.Circle((1.2, 6.7), 0.35, fc="#e2e8f0", ec="#0f172a", lw=2) # head
    ax.add_patch(circle1)
    ax.plot([0.7, 1.7], [6.0, 6.0], color="#0f172a", lw=2) # arms
    ax.plot([1.2, 0.8], [5.6, 4.9], color="#0f172a", lw=2) # leg left
    ax.plot([1.2, 1.6], [5.6, 4.9], color="#0f172a", lw=2) # leg right
    ax.text(1.2, 4.5, 'Registered Tenant\n/ Knowledge Worker', fontsize=10, fontweight='bold', ha='center', va='top')

    # Actor 2: Guest / Visitor
    ax.plot([1.2, 2.3], [1.9, 1.9], color="none") # dummy
    circle2 = plt.Circle((1.2, 2.8), 0.3, fc="#e2e8f0", ec="#0f172a", lw=1.8)
    ax.add_patch(circle2)
    ax.plot([1.2, 1.2], [2.1, 2.5], color="#0f172a", lw=1.8)
    ax.plot([0.8, 1.6], [2.3, 2.3], color="#0f172a", lw=1.8)
    ax.plot([1.2, 0.9], [2.1, 1.5], color="#0f172a", lw=1.8)
    ax.plot([1.2, 1.5], [2.1, 1.5], color="#0f172a", lw=1.8)
    ax.text(1.2, 1.2, 'Guest User\n(Visitor)', fontsize=9, fontweight='bold', ha='center', va='top')

    # Actor 3: Background Worker & AI
    circle3 = plt.Circle((9.7, 5.0), 0.35, fc="#e2e8f0", ec="#0f172a", lw=2)
    ax.add_patch(circle3)
    ax.plot([9.7, 9.7], [4.1, 4.65], color="#0f172a", lw=2)
    ax.plot([9.2, 10.2], [4.4, 4.4], color="#0f172a", lw=2)
    ax.plot([9.7, 9.3], [4.1, 3.5], color="#0f172a", lw=2)
    ax.plot([9.7, 10.1], [4.1, 3.5], color="#0f172a", lw=2)
    ax.text(9.7, 3.1, 'Gemini AI &\nIngestion Worker', fontsize=10, fontweight='bold', ha='center', va='top')

    # Use Case Ellipses
    cases = [
        ("UC1: Browse Platform & Docs", 7.6),
        ("UC2: 1-Click Download Desktop .exe", 6.7),
        ("UC3: Authenticate (RLS Session)", 5.8),
        ("UC4: Configure Custom Bot (10 Avatars)", 4.9),
        ("UC5: Upload Documents (PDF/TXT)", 4.0),
        ("UC6: Async Text Chunking & Embed", 3.1),
        ("UC7: Query Knowledge Base (RAG)", 2.2),
        ("UC8: Stream Grounded Answer", 1.3)
    ]

    for title, y_pos in cases:
        el = FancyBboxPatch((3.0, y_pos - 0.3), 5.0, 0.65, boxstyle="round,pad=0.2", 
                            fc="#ffffff", ec="#3b82f6", lw=1.4)
        ax.add_patch(el)
        ax.text(5.5, y_pos, title, fontsize=9.5, fontweight='bold', color="#1e3a8a", ha='center', va='center')

    # Lines connecting Actors to Use Cases
    # Guest
    ax.plot([1.6, 3.0], [2.2, 7.6], color="#64748b", lw=1.2)
    ax.plot([1.6, 3.0], [2.0, 6.7], color="#64748b", lw=1.2)

    # Tenant
    ax.plot([1.7, 3.0], [5.8, 5.8], color="#0284c7", lw=1.4)
    ax.plot([1.7, 3.0], [5.6, 4.9], color="#0284c7", lw=1.4)
    ax.plot([1.7, 3.0], [5.4, 4.0], color="#0284c7", lw=1.4)
    ax.plot([1.7, 3.0], [5.2, 2.2], color="#0284c7", lw=1.4)

    # Worker / Gemini
    ax.plot([8.0, 9.2], [4.0, 4.8], color="#7c3aed", lw=1.4)
    ax.plot([8.0, 9.2], [3.1, 4.6], color="#7c3aed", lw=1.4)
    ax.plot([8.0, 9.2], [2.2, 4.4], color="#7c3aed", lw=1.4)
    ax.plot([8.0, 9.2], [1.3, 4.2], color="#7c3aed", lw=1.4)

    plt.tight_layout()
    plt.savefig('e:/cortexa-frontend/cortexa/docs/diagrams/use_case_diagram.png', dpi=300)
    plt.close()
    print('Generated use_case_diagram.png')

def create_class_diagram():
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    ax.text(6, 9.6, 'Figure 5.3: CORTEXA UML Class Diagram', 
            fontsize=14, fontweight='bold', ha='center', va='center', fontfamily='serif')

    def draw_class(x, y, w, h, title, attrs, methods, color="#f8fafc", border="#3b82f6"):
        box = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0", fc=color, ec=border, lw=1.5)
        ax.add_patch(box)
        # Header
        header = FancyBboxPatch((x, y + h - 0.45), w, 0.45, boxstyle="square,pad=0", fc="#e2e8f0", ec=border, lw=1.5)
        ax.add_patch(header)
        ax.text(x + w/2, y + h - 0.23, title, fontsize=9.5, fontweight='bold', ha='center', va='center')
        
        # Attributes
        attr_y = y + h - 0.65
        for a in attrs:
            ax.text(x + 0.12, attr_y, a, fontsize=7.5, ha='left', va='center', fontfamily='monospace')
            attr_y -= 0.22

        # Separator
        sep_y = y + (h * 0.45)
        ax.plot([x, x + w], [sep_y, sep_y], color=border, lw=1)

        # Methods
        meth_y = sep_y - 0.22
        for m in methods:
            ax.text(x + 0.12, meth_y, m, fontsize=7.5, ha='left', va='center', fontfamily='monospace')
            meth_y -= 0.22

    # Class 1: Tenant
    draw_class(0.5, 6.2, 3.2, 2.8, "Tenant", 
               ["+ id: UUID", "+ name: String", "+ rls_role: String", "+ created_at: Timestamp"],
               ["+ validate_quota(): Boolean", "+ get_bots(): List<Chatbot>", "+ get_documents(): List<Doc>"])

    # Class 2: Chatbot
    draw_class(4.4, 6.2, 3.2, 2.8, "Chatbot",
               ["+ id: UUID", "+ tenant_id: UUID", "+ name: String", "+ avatar_id: String (1-10)", "+ system_prompt: Text"],
               ["+ update_config(): Void", "+ stream_chat(): AsyncStream", "+ get_context(): VectorResult"])

    # Class 3: User
    draw_class(8.3, 6.2, 3.2, 2.8, "User",
               ["+ id: UUID", "+ tenant_id: UUID", "+ email: String", "+ role: UserRole"],
               ["+ authenticate(): JWTToken", "+ create_bot(): Chatbot", "+ upload_doc(): Document"])

    # Class 4: Document
    draw_class(0.5, 1.8, 3.2, 3.2, "Document",
               ["+ id: UUID", "+ tenant_id: UUID", "+ filename: String", "+ mime_type: String", "+ status: IngestionStatus"],
               ["+ parse_text(): String", "+ sanitize(): String", "+ split_chunks(): List<Chunk>", "+ set_ready(): Void"])

    # Class 5: DocumentChunk
    draw_class(4.4, 1.8, 3.2, 3.2, "DocumentChunk",
               ["+ id: UUID", "+ document_id: UUID", "+ chunk_index: Integer", "+ content: Text", "+ embedding: Vector(768)"],
               ["+ cosine_similarity(): Float", "+ get_preview(): String"])

    # Class 6: EmbeddingService & VectorStore
    draw_class(8.3, 1.8, 3.2, 3.2, "VectorStore",
               ["+ connection: SupabaseClient", "+ model: gemini-embedding-001", "+ dimensions: 768"],
               ["+ embed_text(text): Float[768]", "+ match_documents(): List<Match>", "+ enforce_tenant_rls(): Void"])

    # Relationships
    # Tenant to Chatbot (1 to *)
    ax.annotate('', xy=(4.4, 7.6), xytext=(3.7, 7.6), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(3.9, 7.8, "1..*", fontsize=8, fontweight='bold')

    # User to Tenant (* to 1)
    ax.annotate('', xy=(3.7, 8.4), xytext=(8.3, 8.4), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(7.6, 8.6, "*..1", fontsize=8, fontweight='bold')

    # Tenant to Document (1 to *)
    ax.annotate('', xy=(2.1, 5.0), xytext=(2.1, 6.2), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(2.2, 5.5, "1..*", fontsize=8, fontweight='bold')

    # Document to DocumentChunk (1 to *)
    ax.annotate('', xy=(4.4, 3.4), xytext=(3.7, 3.4), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(3.9, 3.6, "1..*", fontsize=8, fontweight='bold')

    # DocumentChunk to VectorStore
    ax.annotate('', xy=(8.3, 3.4), xytext=(7.6, 3.4), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(7.8, 3.6, "stores in", fontsize=8)

    plt.tight_layout()
    plt.savefig('e:/cortexa-frontend/cortexa/docs/diagrams/class_diagram.png', dpi=300)
    plt.close()
    print('Generated class_diagram.png')

def create_sequence_diagram():
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    ax.text(6, 9.6, 'Figure 5.4: CORTEXA Sequence Diagram (RAG Query Execution)', 
            fontsize=14, fontweight='bold', ha='center', va='center', fontfamily='serif')

    participants = [
        ("User / Client\n(Web/Desktop)", 1.2),
        ("FastAPI Gateway\n(/api/v1/chat)", 3.6),
        ("Embedding Engine\n(Gemini 768-d)", 6.0),
        ("Supabase\n(pgvector + RLS)", 8.4),
        ("Gemini 1.5 Flash\n(LLM Generator)", 10.6)
    ]

    for name, x in participants:
        box = FancyBboxPatch((x - 0.9, 8.4), 1.8, 0.7, boxstyle="round,pad=0.1", fc="#f1f5f9", ec="#334155", lw=1.2)
        ax.add_patch(box)
        ax.text(x, 8.75, name, fontsize=8, fontweight='bold', ha='center', va='center')
        ax.plot([x, x], [0.8, 8.4], color="#94a3b8", linestyle="--", lw=1.2)

    def message(y, x1, x2, label, is_return=False):
        style = "->"
        line_style = ":" if is_return else "-"
        color = "#16a34a" if is_return else "#2563eb"
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle=style, color=color, lw=1.4, linestyle=line_style))
        mid_x = (x1 + x2) / 2
        ax.text(mid_x, y + 0.18, label, fontsize=8, ha='center', va='bottom', 
                color="#0f172a", bbox=dict(boxstyle="square,pad=0.1", fc="#ffffff", ec="none"))

    # Flow sequence
    message(7.8, 1.2, 3.6, "1. POST /api/v1/chat (prompt, tenant_id)")
    message(7.0, 3.6, 6.0, "2. embed_query(prompt)")
    message(6.2, 6.0, 3.6, "3. Return 768-d Query Vector", is_return=True)
    message(5.4, 3.6, 8.4, "4. RPC match_page_sections(vector, tenant_rls)")
    message(4.6, 8.4, 3.6, "5. Return Top-K Ranked Chunks", is_return=True)
    message(3.8, 3.6, 10.6, "6. generate_stream(Context + Prompt)")
    message(3.0, 10.6, 3.6, "7. SSE Token Stream Chunks", is_return=True)
    message(2.2, 3.6, 1.2, "8. Real-time Stream Rendered in UI", is_return=True)
    message(1.4, 1.2, 1.2, "9. Display Grounded Answer with Citations")

    plt.tight_layout()
    plt.savefig('e:/cortexa-frontend/cortexa/docs/diagrams/sequence_diagram.png', dpi=300)
    plt.close()
    print('Generated sequence_diagram.png')

def create_activity_diagram():
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis('off')

    ax.text(5, 10.6, 'Figure 5.5: CORTEXA Document Ingestion Activity Diagram', 
            fontsize=14, fontweight='bold', ha='center', va='center', fontfamily='serif')

    # Initial Node (Black circle)
    init_circle = plt.Circle((5, 9.9), 0.22, fc="#0f172a", ec="#0f172a")
    ax.add_patch(init_circle)
    ax.text(5, 10.25, 'Start', fontsize=9, fontweight='bold', ha='center')

    # Activity steps
    activities = [
        ("User Uploads Document (.PDF / .TXT)", 9.0),
        ("Validate File Format & Size Limits", 8.0),
        ("Save Raw File to Cloud Object Storage", 7.0),
        ("Publish Job to Redis Stream ('cortexa:ingestion')", 6.0),
        ("Background Ingestion Worker Dequeues Job", 5.0),
        ("Extract Text with PyPDF & Clean Control Characters", 4.0),
        ("Partition into Semantic Chunks (500 tokens, 50 overlap)", 3.0),
        ("Generate Gemini Embeddings & Bulk Insert to pgvector", 2.0),
        ("Update Status to 'READY' & Emit Real-time Toast", 1.0)
    ]

    ax.annotate('', xy=(5, 9.3), xytext=(5, 9.7), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.5))

    for idx, (step, y) in enumerate(activities):
        box = FancyBboxPatch((1.8, y - 0.35), 6.4, 0.65, boxstyle="round,pad=0.2", 
                             fc="#eff6ff", ec="#2563eb", lw=1.4)
        ax.add_patch(box)
        ax.text(5, y, step, fontsize=8.5, fontweight='bold', color="#1e3a8a", ha='center', va='center')
        
        if idx < len(activities) - 1:
            next_y = activities[idx+1][1]
            ax.annotate('', xy=(5, next_y + 0.35), xytext=(5, y - 0.35), 
                        arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.5))

    # Final Node (Bullseye)
    ax.annotate('', xy=(5, 0.45), xytext=(5, 0.65), arrowprops=dict(arrowstyle="->", color="#0f172a", lw=1.5))
    outer_final = plt.Circle((5, 0.3), 0.25, fc="#ffffff", ec="#0f172a", lw=1.5)
    inner_final = plt.Circle((5, 0.3), 0.16, fc="#0f172a", ec="#0f172a")
    ax.add_patch(outer_final)
    ax.add_patch(inner_final)
    ax.text(5, -0.05, 'Document Ingestion Complete', fontsize=9, fontweight='bold', ha='center')

    plt.tight_layout()
    plt.savefig('e:/cortexa-frontend/cortexa/docs/diagrams/activity_diagram.png', dpi=300)
    plt.close()
    print('Generated activity_diagram.png')

if __name__ == '__main__':
    create_system_architecture()
    create_use_case_diagram()
    create_class_diagram()
    create_sequence_diagram()
    create_activity_diagram()
    print('All 5 diagrams successfully generated as PNG!')
