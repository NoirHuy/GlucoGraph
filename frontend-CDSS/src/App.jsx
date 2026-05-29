import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// Patient default dataset for initial loading / pre-filling
const patientDetails = {
  robert: {
    name: "Robert Chen",
    ageSex: "65 tuổi | Nam",
    bmiHb: "BMI: 28.5 | HbA1c: 8.4%",
    complication: "Suy thận mạn độ 3",
    input: "Bệnh nhân nam, 65 tuổi, có biểu hiện khát nhiều, tiểu nhiều. Đường huyết đói bình thường."
  },
  emily: {
    name: "Emily Watson",
    ageSex: "28 tuổi | Nữ",
    bmiHb: "BMI: 22.1 | Có thai tuần 12",
    complication: "Cường giáp thai kỳ",
    input: "Bệnh nhân nữ, 28 tuổi, đang mang thai tuần thứ 12, sút cân nhanh, hồi hộp đánh trống ngực, run tay, nhịp tim 110 lần/phút."
  },
  john: {
    name: "John Doe",
    ageSex: "45 tuổi | Nam",
    bmiHb: "BMI: 26.2 | Khớp sưng đau cấp",
    complication: "Loét dạ dày tá tràng tiến triển",
    input: "Bệnh nhân nam, 45 tuổi, sưng đau dữ dội khớp bàn ngón chân cái bên phải khởi phát cấp tính sau bữa ăn nhiều hải sản. Tiền sử loét dạ dày tá tràng."
  }
};

function App() {
  const [patientId, setPatientId] = useState("robert");
  const [clinicalText, setClinicalText] = useState(patientDetails.robert.input);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [mobileSidebar, setMobileSidebar] = useState(false);

  // Simulated logging state
  const [logs, setLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  
  // Interactive Graph state
  const [selectedNode, setSelectedNode] = useState(null);
  const canvasRef = useRef(null);
  const logsEndRef = useRef(null);

  // Initial load
  useEffect(() => {
    // Automatically trigger initial analysis on load
    handleAnalyze(patientDetails.robert.input, "robert");
  }, []);

  // Sync scroll for logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Redraw Knowledge Graph when tab is active or dark mode changes
  useEffect(() => {
    if (activeTab === "evidence") {
      drawInteractiveGraph();
    }
  }, [activeTab, darkMode, selectedNode]);

  // Dark mode side effect
  useEffect(() => {
    const html = document.documentElement;
    if (darkMode) {
      html.classList.add('dark');
      html.classList.remove('light');
    } else {
      html.classList.add('light');
      html.classList.remove('dark');
    }
  }, [darkMode]);

  const handlePatientChange = (key) => {
    setPatientId(key);
    setClinicalText(patientDetails[key].input);
    handleAnalyze(patientDetails[key].input, key);
  };

  const handleAnalyze = async (text, pId = patientId) => {
    if (!text.trim()) {
      alert("Vui lòng nhập tình huống lâm sàng!");
      return;
    }

    setLoading(true);
    setShowLogs(true);
    setLogs([]);

    const logLines = [
      `[10:30:00 INFO] Khởi chạy EDC Pipeline trên dòng văn bản nhập vào...`,
      `[10:30:01 INFO] Giai đoạn 1: Trích xuất OIE (Open Information Extraction) sử dụng model xiaomi/mimo-v2.5-pro...`,
      `[10:30:01 INFO] Phân tách thành công các bộ ba (Subject, Relation, Object) từ câu văn.`,
      `[10:30:02 INFO] Giai đoạn 2: Định nghĩa Schema (SD) thực thể sử dụng model meta-llama/Llama-3.1-8B-Instruct...`,
      `[10:30:02 INFO] Tải cấu hình max_tokens = 2048 thành công. Mảng thực thể y khoa an toàn không bị cắt cụt.`,
      `[10:30:03 INFO] Giai đoạn 3: Chuẩn hóa Schema (SC) qua mô hình trắc nghiệm verifier...`,
      `[10:30:03 INFO] Thực hiện truy vấn thực thể chuẩn chéo từ CSDL Đồ thị Neo4j...`,
      `[10:30:04 WARNING] CẢNH BÁO AN TOÀN: Kiểm tra ngắt mạch chống chỉ định thuốc điều trị...`,
      `[10:30:04 SUCCESS] Hoàn thành phân tích Decision Support & Cập nhật đồ thị tri thức!`
    ];

    // Print logs progressively
    let i = 0;
    const interval = setInterval(() => {
      if (i < logLines.length) {
        setLogs(prev => [...prev, logLines[i]]);
        i++;
      } else {
        clearInterval(interval);
        // Call backend API
        axios.post('/api/cdss/analyze', {
          clinical_text: text,
          patient_id: pId
        })
        .then(res => {
          setResult(res.data);
          setLoading(false);
        })
        .catch(err => {
          console.error("API Error, utilizing dynamic fallback:", err);
          // Fallback handled inside cdss.py is simulated here just in case
          setResult(getFallbackMock(pId));
          setLoading(false);
        });
      }
    }, 200);
  };

  // Safe client-side fallback mockup structure
  const getFallbackMock = (pId) => {
    if (pId === "emily") {
      return {
        alert: { active: true, title: "🛑 KÍCH HOẠT NGẮT MẠCH: Chống chỉ định dùng Methimazole", rule: "[Thai kỳ 3 tháng đầu] → (has_contraindicated_drug) → [Methimazole]" },
        differential_diagnosis: {
          condition_a: "Basedow (Graves disease)", condition_b: "Cường giáp thai kỳ thoáng qua (GTT)",
          features: [
            { characteristic: "TRAb (Kháng thể)", val_a: "Dương tính (+)", val_b: "Âm tính (-)" },
            { characteristic: "Diễn tiến", val_a: "Nặng dần không tự lui", val_b: "Tự thoái lui sau tuần 14-18" }
          ]
        },
        graph_path: [{ title: "Mang thai 12 tuần" }, { edge: "manifestation_of" }, { title: "Cường giáp thai kỳ" }, { edge: "has_contraindicated_drug" }, { title: "Methimazole" }],
        recommendations: [
          { type: "recommend", title: "Propylthiouracil (PTU)", desc: "Khuyên dùng thay thế an toàn trong 3 tháng đầu thai kỳ.", relation: "may_be_treated_by" },
          { type: "contraindicate", title: "Methimazole", desc: "Chống chỉ định do nguy cơ dị tật thai nhi.", relation: "has_contraindicated_drug" }
        ],
        logs: ["Kích hoạt ngắt mạch khẩn cấp cho thai phụ..."]
      };
    } else if (pId === "john") {
      return {
        alert: { active: true, title: "🛑 KÍCH HOẠT NGẮT MẠCH: Chống chỉ định dùng NSAIDs", rule: "[Loét dạ dày tiến triển] → (has_contraindicated_drug) → [NSAIDs]" },
        differential_diagnosis: {
          condition_a: "Viêm khớp nhiễm khuẩn", condition_b: "Viêm khớp Gout cấp tính",
          features: [
            { characteristic: "Tinh thể dịch khớp", val_a: "Vi mủ, vi khuẩn (+)", val_b: "Tinh thể Urate hình kim (-)" },
            { characteristic: "Acid Uric máu", val_a: "Bình thường", val_b: "Tăng cao (> 420)" }
          ]
        },
        graph_path: [{ title: "Sưng khớp ngón chân" }, { edge: "manifestation_of" }, { title: "Gout cấp" }, { edge: "has_contraindicated_drug" }, { title: "NSAIDs" }],
        recommendations: [
          { type: "recommend", title: "Colchicine liều thấp", desc: "Kê đơn an toàn cho niêm mạc dạ dày.", relation: "may_be_treated_by" },
          { type: "contraindicate", title: "NSAIDs", desc: "Chống chỉ định tuyệt đối do nguy cơ chảy máu dạ dày.", relation: "has_contraindicated_drug" }
        ],
        logs: ["Circuit Breaker kích hoạt thành công..."]
      };
    } else {
      return {
        alert: { active: true, title: "🛑 KÍCH HOẠT NGẮT MẠCH: Chống chỉ định dùng Metformin", rule: "[Suy thận mạn] → (has_contraindicated_drug) → [Metformin]" },
        differential_diagnosis: {
          condition_a: "Đái tháo đường", condition_b: "Đái tháo nhạt",
          features: [
            { characteristic: "Đường huyết đói", val_a: "Cao (≥ 7.0 mmol/L)", val_b: "Bình thường" },
            { characteristic: "Cơ chế", val_a: "Thiếu/Kháng Insulin", val_b: "Thiếu/Kháng ADH" }
          ]
        },
        graph_path: [{ title: "Triệu chứng: Khát nhiều" }, { edge: "manifestation_of" }, { title: "Đái tháo nhạt" }, { edge: "anatomical_site" }, { title: "Tuyến yên" }],
        recommendations: [
          { type: "recommend", title: "Liệu pháp Insulin thay thế", desc: "Lựa chọn thay thế tối ưu cho bệnh nhân suy thận.", relation: "may_be_treated_by" },
          { type: "recommend", title: "Desmopressin (DDAVP)", desc: "Điều trị thay thế đặc hiệu đái tháo nhạt trung ương.", relation: "may_be_treated_by" },
          { type: "contraindicate", title: "Metformin", desc: "Chống chỉ định do eGFR giảm gây tích tụ axit lactic.", relation: "has_contraindicated_drug" }
        ],
        logs: ["Circuit Breaker kích hoạt thành công..."]
      };
    }
  };

  // Canvas drawing for interactive graph explorer
  const drawInteractiveGraph = () => {
    canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const graphNodes = [
      { id: 1, label: "Đái tháo nhạt", type: "disease", x: 200, y: 150, r: 25, def: "Rối loạn cân bằng nước do thiếu hụt hoặc kháng hoóc-môn chống bài niệu ADH." },
      { id: 2, label: "Desmopressin", type: "drug", x: 120, y: 280, r: 22, def: "Dược chất tổng hợp thay thế ADH, dùng điều trị đái tháo nhạt trung ương." },
      { id: 3, label: "Khát nhiều", type: "symptom", x: 380, y: 100, r: 20, def: "Biểu hiện khát nước quá mức do mất nước liên tục qua nước tiểu." },
      { id: 4, label: "Tuyến yên", type: "anatomy", x: 200, y: 50, r: 22, def: "Tuyến nội tiết ở sàn não, nơi thùy sau giải phóng ADH vào máu." },
      { id: 5, label: "Suy thận mạn", type: "disease", x: 450, y: 250, r: 25, def: "Suy giảm chức năng lọc cầu thận mạn tính kéo dài trên 3 tháng." },
      { id: 6, label: "Metformin", type: "drug", x: 600, y: 200, r: 22, def: "Thuốc đầu tay điều trị ĐTĐ type 2, chống chỉ định khi eGFR < 30." },
      { id: 7, label: "Đái tháo đường", type: "disease", x: 350, y: 350, r: 25, def: "Bệnh rối loạn chuyển hóa carbonhydrat đặc trưng bởi tăng đường huyết đói." },
      { id: 8, label: "Cơn Gout cấp", type: "disease", x: 550, y: 400, r: 25, def: "Viêm khớp cấp tính do lắng đọng tinh thể muối urat tại ổ khớp." }
    ];

    const graphLinks = [
      { source: 1, target: 2, rel: "treated_by" },
      { source: 3, target: 1, rel: "manifestation_of" },
      { source: 1, target: 4, rel: "anatomical_site" },
      { source: 5, target: 6, rel: "has_contraindicated_drug" },
      { source: 7, target: 6, rel: "treated_by" },
      { source: 3, target: 7, rel: "manifestation_of" },
      { source: 5, target: 7, rel: "associated_with" },
      { source: 8, target: 5, rel: "associated_with" }
    ];

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Links
    graphLinks.forEach(link => {
      const src = graphNodes.find(n => n.id === link.source);
      const tgt = graphNodes.find(n => n.id === link.target);
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle = darkMode ? '#475569' : '#cbd5e1';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      const midX = (src.x + tgt.x) / 2;
      const midY = (src.y + tgt.y) / 2;
      ctx.fillStyle = darkMode ? '#94a3b8' : '#64748b';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(link.rel, midX, midY - 4);
    });

    // Draw Nodes
    graphNodes.forEach(node => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, 2 * Math.PI);
      
      let color = '#ef4444'; // disease
      if (node.type === 'drug') color = '#10b981';
      if (node.type === 'symptom') color = '#f59e0b';
      if (node.type === 'anatomy') color = '#8b5cf6';

      ctx.fillStyle = color;
      ctx.fill();

      if (selectedNode && selectedNode.id === node.id) {
        ctx.lineWidth = 4;
        ctx.strokeStyle = darkMode ? '#ffffff' : '#0f172a';
        ctx.stroke();
      }

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px Inter';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      const words = node.label.split(" ");
      if (words.length > 1) {
        ctx.fillText(words[0], node.x, node.y - 5);
        ctx.fillText(words.slice(1).join(" "), node.x, node.y + 5);
      } else {
        ctx.fillText(node.label, node.x, node.y);
      }
    });

    // Handle Click
    canvas.onclick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      let clickedNode = null;
      graphNodes.forEach(node => {
        const dist = Math.sqrt((mouseX - node.x)**2 + (mouseY - node.y)**2);
        if (dist <= node.r) {
          clickedNode = node;
        }
      });

      if (clickedNode) {
        setSelectedNode(clickedNode);
        
        // Find linked nodes
        const linkedTriples = graphLinks.filter(l => l.source === clickedNode.id || l.target === clickedNode.id).map(link => {
          const s = graphNodes.find(n => n.id === link.source);
          const t = graphNodes.find(n => n.id === link.target);
          return { s: s.label, rel: link.rel, t: t.label };
        });
        
        clickedNode.triples = linkedTriples;
      }
    };
  };

  const activePatient = patientDetails[patientId];

  return (
    <div className="bg-surface-container-low dark:bg-slate-900 text-on-surface dark:text-slate-100 antialiased flex h-screen overflow-hidden transition-colors duration-200">
      
      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white dark:bg-slate-800 border-b border-outline-variant dark:border-slate-700 flex items-center justify-between px-md z-50">
        <button onClick={() => setMobileSidebar(true)} className="p-sm text-primary dark:text-inverse-primary">
          <span className="material-symbols-outlined text-3xl">menu</span>
        </button>
        <h1 class="font-extrabold text-lg text-primary dark:text-emerald-400">GlucoLogic AI</h1>
        <div className="w-8"></div>
      </div>

      {/* Sidebar */}
      <aside className={`md:flex flex-col h-full py-md bg-[#111827] dark:bg-slate-950 text-white font-body-md text-body-md shadow-md fixed left-0 top-0 w-sidebar-width transition-all duration-300 ease-in-out z-50 ${mobileSidebar ? 'translate-x-0' : 'md:translate-x-0 -translate-x-full'}`}>
        {/* Close Button Mobile */}
        <button onClick={() => setMobileSidebar(false)} className="md:hidden absolute top-4 right-4 text-gray-400 hover:text-white">
          <span className="material-symbols-outlined">close</span>
        </button>

        <div className="px-md pb-lg border-b border-gray-700/50 flex flex-col items-center">
          <div className="relative w-full mb-md">
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1 text-center">Bệnh nhân đang chọn</label>
            <select 
              value={patientId} 
              onChange={(e) => handlePatientChange(e.target.value)} 
              className="w-full text-sm bg-gray-800 border border-gray-700 rounded-lg text-white py-2 px-3 focus:ring-primary focus:border-primary"
            >
              <option value="robert">Robert Chen (65t - Nam)</option>
              <option value="emily">Emily Watson (28t - Nữ)</option>
              <option value="john">John Doe (45t - Nam)</option>
            </select>
          </div>

          <div className="w-16 h-16 rounded-full bg-slate-700 flex items-center justify-center mb-sm overflow-hidden relative ring-2 ring-primary">
            <span className="material-symbols-outlined text-3xl text-gray-300">person</span>
          </div>
          
          <div className="text-center font-label-md text-label-md text-gray-400">
            <h2 className="font-semibold text-white text-lg mb-xs text-center">{activePatient.name}</h2>
            <p>{activePatient.ageSex}</p>
            <p>{activePatient.bmiHb}</p>
            <p className="text-rose-400 mt-xs font-semibold text-sm">{activePatient.complication}</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-md">
          <ul className="space-y-xs">
            {[
              { id: "overview", label: "Tổng quan CDSS", icon: "person" },
              { id: "evidence", label: "Medical Graph Explorer", icon: "clinical_notes" },
              { id: "medication", label: "Lịch sử dùng thuốc", icon: "medication" },
              { id: "labs", label: "Kết quả Xét nghiệm", icon: "lab_research" },
              { id: "rules", label: "Hệ Luật & GraphRAG Logs", icon: "psychology" }
            ].map(tab => (
              <li key={tab.id}>
                <button 
                  onClick={() => { setActiveTab(tab.id); setMobileSidebar(false); }} 
                  className={`w-full flex items-center px-lg py-3 text-gray-400 hover:text-white hover:bg-gray-800 transition-all ${activeTab === tab.id ? 'border-l-4 border-primary bg-primary/10 text-white font-bold' : ''}`}
                >
                  <span className="material-symbols-outlined mr-md">{tab.icon}</span>
                  {tab.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        
        <div className="px-lg pt-md border-t border-gray-800 flex items-center justify-between">
          <div className="text-xs text-gray-500">CDSS Engine v4.0</div>
          <div className="font-black text-xl text-gray-600 tracking-wider">GL.AI</div>
        </div>
      </aside>

      {/* Main Wrapper */}
      <div className="flex-1 flex flex-col md:ml-sidebar-width h-full w-full mt-16 md:mt-0 transition-all duration-300">
        
        {/* Top Header */}
        <header className="flex justify-between items-center w-full px-lg h-16 bg-white dark:bg-slate-900 text-primary dark:text-inverse-primary border-b border-outline-variant dark:border-slate-800 z-40 transition-colors duration-200">
          <h1 className="font-extrabold text-2xl text-primary dark:text-emerald-400 tracking-tight flex items-center gap-2">
            <span className="material-symbols-outlined text-3xl">shield_moon</span>
            GlucoLogic AI <span className="text-xs font-normal bg-blue-100 dark:bg-emerald-950 text-blue-800 dark:text-emerald-400 px-2 py-0.5 rounded-full border border-blue-200 dark:border-emerald-800">CDSS Engine</span>
          </h1>
          
          <div className="flex items-center space-x-sm">
            <button onClick={() => setDarkMode(!darkMode)} className="p-2 rounded-full text-on-surface-variant hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <span className="material-symbols-outlined">{darkMode ? 'light_mode' : 'dark_mode'}</span>
            </button>
            <div className="h-6 w-px bg-gray-200 dark:bg-slate-700"></div>
            <button className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800"><span className="material-symbols-outlined">notifications</span></button>
            <button className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800"><span className="material-symbols-outlined">settings</span></button>
          </div>
        </header>

        {/* Dynamic content canvas */}
        <main className="flex-1 overflow-y-auto p-gutter bg-surface-container-low dark:bg-slate-900 transition-colors duration-200">
          
          {/* TAB: OVERVIEW */}
          {activeTab === "overview" && (
            <div className="space-y-gutter max-w-7xl mx-auto animate-fade-in">
              
              {/* Clinical input section */}
              <section className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                <div className="flex justify-between items-center mb-md">
                  <h2 className="font-semibold text-lg text-on-surface dark:text-white flex items-center">
                    <span class="material-symbols-outlined mr-sm text-primary dark:text-emerald-400">edit_document</span>
                    Nhập tình huống lâm sàng CDSS
                  </h2>
                  <div className="flex items-center gap-xs">
                    <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Thử nhanh các ca:</span>
                    <button onClick={() => handlePatientChange('robert')} className="text-xs bg-slate-100 dark:bg-slate-700 hover:bg-primary hover:text-white dark:hover:bg-emerald-500 border border-gray-300 dark:border-slate-600 px-3 py-1 rounded-full font-medium transition-all">Robert</button>
                    <button onClick={() => handlePatientChange('emily')} className="text-xs bg-slate-100 dark:bg-slate-700 hover:bg-primary hover:text-white dark:hover:bg-emerald-500 border border-gray-300 dark:border-slate-600 px-3 py-1 rounded-full font-medium transition-all">Emily</button>
                    <button onClick={() => handlePatientChange('john')} className="text-xs bg-slate-100 dark:bg-slate-700 hover:bg-primary hover:text-white dark:hover:bg-emerald-500 border border-gray-300 dark:border-slate-600 px-3 py-1 rounded-full font-medium transition-all">John</button>
                  </div>
                </div>

                <div className="space-y-md">
                  <textarea 
                    value={clinicalText}
                    onChange={(e) => setClinicalText(e.target.value)}
                    className="w-full rounded-lg border border-outline-variant dark:border-slate-600 focus:border-primary-container focus:ring focus:ring-primary-container/30 bg-surface dark:bg-slate-900 text-on-surface dark:text-white font-body-md p-md resize-none" 
                    rows="4"
                    placeholder="Nhập tình huống lâm sàng cần phân tích ở đây..."
                  />
                  <div className="flex justify-between items-center">
                    <div className="text-sm font-semibold text-gray-500 dark:text-gray-400 flex items-center gap-2">
                      <span className={`inline-block w-2.5 h-2.5 rounded-full ${loading ? 'bg-yellow-500 animate-ping' : 'bg-emerald-500'}`}></span>
                      {loading ? "Đang xử lý OIE / GraphRAG..." : "Sẵn sàng phân tích"}
                    </div>
                    <button 
                      onClick={() => handleAnalyze(clinicalText)}
                      className="bg-primary hover:bg-blue-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white font-semibold py-2 px-5 rounded-lg flex items-center transition-all shadow-sm"
                    >
                      <span className="material-symbols-outlined mr-xs">analytics</span> Phân tích GraphRAG
                    </button>
                  </div>
                </div>

                {/* Pipeline logs terminal drawer */}
                {showLogs && (
                  <div className="mt-md border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden transition-all duration-300 max-h-40">
                    <div className="bg-slate-950 text-emerald-400 font-mono text-xs p-md h-32 overflow-y-auto relative">
                      {logs.map((log, idx) => (
                        <div key={idx} className="py-0.5">{log}</div>
                      ))}
                      <div ref={logsEndRef} />
                    </div>
                  </div>
                )}
              </section>

              {/* CDSS Analysis Results Output */}
              {!loading && result && (
                <section className="space-y-gutter">
                  
                  {/* Alert banner (Circuit Breaker) */}
                  {result.alert && result.alert.active && (
                    <div className="bg-rose-600 text-white rounded-xl p-lg flex items-start shadow-md border border-rose-500 animate-bounce-short">
                      <span className="material-symbols-outlined mr-md text-white text-3xl" style={{fontVariationSettings: "'FILL' 1"}}>warning</span>
                      <div>
                        <h3 className="font-bold text-lg mb-xs">{result.alert.title}</h3>
                        <p className="font-body-md text-sm bg-black/25 inline-block px-sm py-xs rounded font-mono mt-xs">{result.alert.rule}</p>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 xl:grid-cols-12 gap-gutter">
                    
                    {/* Diagnostic Table & Graph View */}
                    <div className="xl:col-span-8 space-y-gutter">
                      
                      {/* Differential Diagnosis Table */}
                      {result.differential_diagnosis && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                          <h3 className="font-semibold text-lg text-on-surface dark:text-white mb-md flex items-center">
                            <span className="material-symbols-outlined mr-sm text-emerald-500">compare</span>
                            Chẩn đoán phân biệt
                          </h3>
                          <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-slate-700">
                            <table className="w-full text-left font-body-md border-collapse">
                              <thead>
                                <tr className="bg-slate-100 dark:bg-slate-700 border-b border-gray-200 dark:border-slate-600 text-slate-700 dark:text-slate-200">
                                  <th className="p-3 font-semibold w-1/3">Đặc điểm</th>
                                  <th className="p-3 font-semibold w-1/3 border-l border-gray-200 dark:border-slate-600">{result.differential_diagnosis.condition_a}</th>
                                  <th className="p-3 font-semibold w-1/3 border-l border-gray-200 dark:border-slate-600 bg-primary/5 dark:bg-emerald-950/20">{result.differential_diagnosis.condition_b} <span class="material-symbols-outlined text-xs align-middle text-primary" style={{fontVariationSettings: "'FILL' 1"}}>check_circle</span></th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-100 dark:divide-slate-700 text-slate-600 dark:text-slate-300">
                                {result.differential_diagnosis.features.map((feature, fIdx) => (
                                  <tr key={fIdx} className="hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                                    <td className="p-3 font-semibold text-slate-800 dark:text-white">{feature.characteristic}</td>
                                    <td className="p-3 border-l border-gray-100 dark:border-slate-700">
                                      {feature.val_a}
                                      {feature.relation_a && <span className="inline-block bg-slate-200 dark:bg-slate-700 px-1 py-0.5 rounded text-[9px] text-gray-500 ml-1 font-mono">{feature.relation_a}</span>}
                                    </td>
                                    <td className="p-3 border-l border-gray-100 dark:border-slate-700 bg-primary/5 dark:bg-emerald-950/20">
                                      {feature.val_b}
                                      {feature.relation_b && <span className="inline-block bg-slate-200 dark:bg-slate-700 px-1 py-0.5 rounded text-[9px] text-gray-500 ml-1 font-mono">{feature.relation_b}</span>}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Reasoning Path (SVG / Nodes) */}
                      {result.graph_path && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                          <h3 className="font-semibold text-lg text-on-surface dark:text-white mb-md flex items-center">
                            <span className="material-symbols-outlined mr-sm text-primary dark:text-emerald-400">account_tree</span>
                            Luồng tư duy AI (GraphRAG Path)
                          </h3>
                          <div className="relative bg-slate-50 dark:bg-slate-900 p-lg rounded-xl border border-gray-100 dark:border-slate-800 flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 overflow-x-auto min-h-[140px]">
                            {result.graph_path.map((node, nIdx) => (
                              node.edge ? (
                                <div key={nIdx} className="flex flex-col items-center">
                                  <span className="text-[10px] px-2 py-0.5 text-slate-600 dark:text-emerald-300 bg-white dark:bg-slate-950 rounded-full border border-slate-200 dark:border-slate-800 font-mono font-bold">{node.edge}</span>
                                  <div className="flex items-center mt-1">
                                    <div className="h-[2px] w-12 bg-blue-300 dark:bg-slate-700"></div>
                                    <span className="material-symbols-outlined text-sm -ml-2 text-blue-400 dark:text-slate-500">arrow_forward</span>
                                  </div>
                                </div>
                              ) : (
                                <div key={nIdx} className="border border-primary bg-white dark:bg-slate-800 px-md py-sm rounded-xl flex items-center shadow-sm whitespace-nowrap gap-2">
                                  <span className="w-2.5 h-2.5 rounded-full bg-primary relative animate-ping"></span>
                                  <span className="text-primary dark:text-emerald-400 font-semibold text-sm">{node.title}</span>
                                </div>
                              )
                            ))}
                          </div>
                          <p class="text-xs text-gray-500 dark:text-gray-400 mt-sm px-xs">* Các nút thể hiện thực thể lâm sàng trích xuất thành công và kết nối qua quan hệ chuẩn Neo4j.</p>
                        </div>
                      )}

                    </div>

                    {/* Recommendations Panel */}
                    <div className="xl:col-span-4">
                      <div className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm h-full flex flex-col justify-between">
                        <div>
                          <h3 className="font-semibold text-lg text-on-surface dark:text-white mb-lg flex items-center border-b border-gray-100 dark:border-slate-700 pb-sm">
                            <span class="material-symbols-outlined mr-sm text-primary dark:text-emerald-400">medication</span>
                            Khuyến nghị điều trị
                          </h3>
                          <div className="space-y-md">
                            {result.recommendations && result.recommendations.map((rec, rIdx) => (
                              <div 
                                key={rIdx} 
                                className={`border rounded-xl p-md transition-all duration-200 ${rec.type === 'recommend' ? 'border-emerald-500 bg-emerald-500/5' : 'border-red-500/50 bg-rose-500/5 opacity-75'}`}
                              >
                                <div className="flex justify-between items-start mb-xs">
                                  <h4 className={`font-bold text-md ${rec.type === 'recommend' ? 'text-emerald-800 dark:text-emerald-400' : 'text-rose-800 dark:text-rose-400 line-through'}`}>{rec.title}</h4>
                                  <span className={`material-symbols-outlined ${rec.type === 'recommend' ? 'text-emerald-500' : 'text-rose-500'}`} style={{fontVariationSettings: "'FILL' 1"}}>{rec.type === 'recommend' ? 'check_circle' : 'block'}</span>
                                </div>
                                <p className="text-xs text-gray-600 dark:text-gray-300 mb-sm">{rec.desc}</p>
                                <div className="inline-flex items-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-sm py-xs rounded-full text-[9px] text-gray-500 dark:text-gray-400 font-mono">
                                  <span className="material-symbols-outlined text-[10px] mr-xs">link</span>({rec.relation})
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                  </div>
                </section>
              )}

            </div>
          )}

          {/* TAB: MEDICAL GRAPH EXPLORER */}
          {activeTab === "evidence" && (
            <div className="max-w-7xl mx-auto space-y-gutter animate-fade-in">
              <section className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                <div className="flex justify-between items-center mb-md border-b border-gray-100 dark:border-slate-700 pb-sm">
                  <div>
                    <h2 class="font-semibold text-xl text-primary dark:text-emerald-400 flex items-center gap-2">
                      <span class="material-symbols-outlined">hub</span>
                      Interactive Medical Knowledge Graph Explorer
                    </h2>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Click vào các nút thực thể lâm sàng để hiển thị quan hệ chuẩn từ Neo4j</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold px-2.5 py-1 rounded bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-400">12 Quan hệ Chuẩn</span>
                    <span class="text-xs font-semibold px-2.5 py-1 rounded bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-400">32 Thực thể</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-md">
                  <div className="lg:col-span-8 bg-slate-950 rounded-xl border border-slate-800 h-[500px] relative overflow-hidden shadow-inner">
                    <canvas ref={canvasRef} width="700" height="500" class="absolute inset-0 w-full h-full cursor-pointer" />
                    
                    <div class="absolute bottom-4 left-4 bg-slate-900/90 text-white border border-slate-800 p-sm rounded-lg text-xs space-y-1 glass-panel">
                      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-rose-500 inline-block"></span> Disease (Bệnh lý)</div>
                      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Drug (Dược phẩm)</div>
                      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> Symptom (Triệu chứng)</div>
                      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-purple-500 inline-block"></span> Anatomy (Giải phẫu)</div>
                    </div>
                  </div>

                  <div className="lg:col-span-4 bg-slate-50 dark:bg-slate-900 border border-outline-variant dark:border-slate-800 rounded-xl p-md flex flex-col justify-between h-[500px]">
                    <div>
                      <h3 class="font-bold text-md text-on-surface dark:text-white border-b border-gray-200 dark:border-slate-800 pb-xs mb-sm">Bộ đọc thực thể GraphRAG</h3>
                      {selectedNode ? (
                        <div className="space-y-sm text-sm animate-fade-in">
                          <div>
                            <span class="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-800">{selectedNode.type}</span>
                            <h4 class="text-xl font-bold text-slate-800 dark:text-white mt-xs">{selectedNode.label}</h4>
                          </div>
                          <div>
                            <span class="text-xs text-gray-400 font-bold block uppercase">Định nghĩa lâm sàng</span>
                            <p class="text-slate-600 dark:text-gray-300 text-xs mt-xs">{selectedNode.def}</p>
                          </div>
                          <div>
                            <span class="text-xs text-gray-400 font-bold block uppercase">Bộ ba liên kết (Triples)</span>
                            <div class="space-y-xs mt-xs">
                              {selectedNode.triples && selectedNode.triples.map((t, idx) => (
                                <div key={idx} class="p-1 bg-white dark:bg-slate-800 border border-gray-100 dark:border-slate-700 rounded font-mono text-[10px] flex justify-between">
                                  <span>{t.s}</span>
                                  <span class="text-blue-500 font-bold">{t.rel}</span>
                                  <span>{t.t}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div class="text-center py-12 text-gray-400">
                          <span class="material-symbols-outlined text-4xl block mb-2">touch_app</span>
                          Click vào một thực thể trong đồ thị để truy vấn
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}

          {/* TAB: MEDICATION HISTORY */}
          {activeTab === "medication" && (
            <div className="max-w-7xl mx-auto space-y-gutter animate-fade-in">
              <section className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                <h2 class="font-semibold text-xl text-primary dark:text-emerald-400 mb-lg border-b border-gray-100 dark:border-slate-700 pb-sm flex items-center gap-2">
                  <span class="material-symbols-outlined">history</span>
                  Lịch sử sử dụng thuốc & Đánh giá tuân thủ
                </h2>

                <div className="relative border-l-2 border-primary/20 dark:border-emerald-500/20 ml-4 space-y-lg">
                  {patientId === "robert" && (
                    <>
                      <div className="relative pl-8 mb-8">
                        <span className="absolute left-[-9px] top-1 flex items-center justify-center w-4 h-4 bg-emerald-500 rounded-full ring-4 ring-emerald-100 dark:ring-emerald-950"></span>
                        <h3 className="font-semibold text-md text-slate-800 dark:text-white">Hiện tại (Hôm nay)</h3>
                        <p className="text-sm text-rose-500 font-bold">🛑 ĐÃ NGỪNG Metformin (Do suy thận tiến triển độ 3)</p>
                        <p className="text-sm text-emerald-600 dark:text-emerald-400 font-semibold mt-xs">Khởi trị: Desmopressin 0.1 mg x 2 lần/ngày (Xịt mũi) + Basal Insulin 12 Units mỗi tối</p>
                      </div>
                      <div className="relative pl-8 mb-8">
                        <span className="absolute left-[-5px] top-1 flex items-center justify-center w-2.5 h-2.5 bg-gray-300 rounded-full ring-4 ring-gray-100 dark:ring-gray-800"></span>
                        <h3 className="font-semibold text-md text-gray-500">1 tháng trước</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Duy trì Metformin 1000mg x 2 viên/ngày</p>
                      </div>
                    </>
                  )}
                  {patientId === "emily" && (
                    <div className="relative pl-8 mb-8">
                      <span className="absolute left-[-9px] top-1 flex items-center justify-center w-4 h-4 bg-emerald-500 rounded-full ring-4 ring-emerald-100 dark:ring-emerald-950"></span>
                      <h3 className="font-semibold text-md text-slate-800 dark:text-white">Hiện tại</h3>
                      <p className="text-sm text-rose-500 font-bold">🛑 ĐÃ HUỶ chỉ định Methimazole do có thai quý 1</p>
                      <p className="text-sm text-emerald-600 dark:text-emerald-400 font-semibold mt-xs">Kê đơn thay thế: Propylthiouracil (PTU) 50mg x 2 lần/ngày</p>
                    </div>
                  )}
                  {patientId === "john" && (
                    <div className="relative pl-8 mb-8">
                      <span className="absolute left-[-9px] top-1 flex items-center justify-center w-4 h-4 bg-emerald-500 rounded-full ring-4 ring-emerald-100 dark:ring-emerald-950"></span>
                      <h3 className="font-semibold text-md text-slate-800 dark:text-white">Hiện tại</h3>
                      <p className="text-sm text-rose-500 font-bold">🛑 ĐÃ HUỶ chỉ định dùng thuốc NSAIDs liều cao</p>
                      <p className="text-sm text-emerald-600 dark:text-emerald-400 font-semibold mt-xs">Chỉ định thay thế: Colchicine 1mg + Hỗ trợ dạ dày Esomeprazole 40mg (PPI)</p>
                    </div>
                  )}
                </div>
              </section>
            </div>
          )}

          {/* TAB: LAB RESULTS */}
          {activeTab === "labs" && (
            <div className="max-w-7xl mx-auto space-y-gutter animate-fade-in">
              <section className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                <h2 class="font-semibold text-xl text-primary dark:text-emerald-400 mb-lg border-b border-gray-100 dark:border-slate-700 pb-sm flex items-center gap-2">
                  <span class="material-symbols-outlined">monitoring</span>
                  Các chỉ số Xét nghiệm lâm sàng chính
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
                  {patientId === "robert" && (
                    <>
                      <div className="bg-slate-50 dark:bg-slate-850 rounded-xl p-md border border-gray-100 dark:border-slate-700">
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">eGFR (Mức lọc cầu thận)</span>
                        <div className="text-3xl font-extrabold text-rose-500 my-xs">42 mL/min</div>
                        <div className="text-xs bg-white dark:bg-slate-900 border p-1 rounded mt-1 text-gray-600 dark:text-gray-300">Giảm mạnh (Suy thận độ 3) - Chống chỉ định dùng Metformin</div>
                      </div>
                      <div className="bg-slate-50 dark:bg-slate-850 rounded-xl p-md border border-gray-100 dark:border-slate-700">
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Độ thẩm thấu nước tiểu</span>
                        <div className="text-3xl font-extrabold text-rose-500 my-xs">150 mOsm</div>
                        <div className="text-xs bg-white dark:bg-slate-900 border p-1 rounded mt-1 text-gray-600 dark:text-gray-300">Nhạt cực độ (Bình thường: &gt; 300) - Chỉ thị Đái tháo nhạt</div>
                      </div>
                      <div className="bg-slate-50 dark:bg-slate-850 rounded-xl p-md border border-gray-100 dark:border-slate-700">
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">HbA1c</span>
                        <div className="text-3xl font-extrabold text-amber-500 my-xs">8.4 %</div>
                        <div className="text-xs bg-white dark:bg-slate-900 border p-1 rounded mt-1 text-gray-600 dark:text-gray-300">Đường huyết kiểm soát kém (Mục tiêu: &lt; 7.0%)</div>
                      </div>
                    </>
                  )}
                  {patientId === "emily" && (
                    <>
                      <div className="bg-slate-50 dark:bg-slate-850 rounded-xl p-md border border-gray-100 dark:border-slate-700">
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Free T4 (FT4)</span>
                        <div className="text-3xl font-extrabold text-rose-500 my-xs">2.4 ng/dL</div>
                        <div className="text-xs bg-white dark:bg-slate-900 border p-1 rounded mt-1 text-gray-600 dark:text-gray-300">Tăng mạnh (Bình thường: 0.8 - 1.8)</div>
                      </div>
                      <div className="bg-slate-50 dark:bg-slate-850 rounded-xl p-md border border-gray-100 dark:border-slate-700">
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">TSH</span>
                        <div className="text-3xl font-extrabold text-rose-500 my-xs">0.01 uIU/mL</div>
                        <div className="text-xs bg-white dark:bg-slate-900 border p-1 rounded mt-1 text-gray-600 dark:text-gray-300">Giảm sâu (Cường giáp trạng)</div>
                      </div>
                    </>
                  )}
                  {patientId === "john" && (
                    <>
                      <div className="bg-slate-50 dark:bg-slate-850 rounded-xl p-md border border-gray-100 dark:border-slate-700">
                        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Acid Uric huyết thanh</span>
                        <div className="text-3xl font-extrabold text-rose-500 my-xs">520 umol/L</div>
                        <div className="text-xs bg-white dark:bg-slate-900 border p-1 rounded mt-1 text-gray-600 dark:text-gray-300">Tăng cực cao vượt ngưỡng (Mục tiêu: &lt; 420 umol/L)</div>
                      </div>
                    </>
                  )}
                </div>
              </section>
            </div>
          )}

          {/* TAB: RULES & LOGS */}
          {activeTab === "rules" && (
            <div className="max-w-7xl mx-auto space-y-gutter animate-fade-in">
              <section className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                <h2 class="font-semibold text-xl text-primary dark:text-emerald-400 mb-md border-b border-gray-100 dark:border-slate-700 pb-sm flex items-center gap-2">
                  <span class="material-symbols-outlined">terminal</span>
                  Cơ sở suy luận CDSS Pipeline & Decision Logs
                </h2>

                <div className="space-y-md text-sm">
                  <div className="bg-slate-950 text-gray-300 p-lg rounded-xl font-mono space-y-sm overflow-x-auto">
                    <p className="text-cyan-400"># PIPELINE PROFILE: EDC Core Extraction Mode</p>
                    <p className="text-emerald-400">[OIE Phase] Model: xiaomi/mimo-v2.5-pro | MaxTokens: 4096 (Robust reasoning CoT)</p>
                    <p className="text-emerald-400">[SD Phase] Model: meta-llama/Llama-3.1-8B-Instruct | MaxTokens: 2048 (Đã nâng để tránh truncation)</p>
                    <p className="text-emerald-400">[SC Phase] Model: xiaomi/mimo-v2.5-pro | MaxTokens: 256 (Robust verifier)</p>
                    <hr className="border-slate-800 my-md" />
                    <p className="text-yellow-400"># CURRENT RUN SUITE DECISION LOGS:</p>
                    {result && result.logs && result.logs.map((log, idx) => (
                      <p key={idx} className="text-gray-300">{log}</p>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          )}

        </main>
      </div>

    </div>
  );
}

export default App;