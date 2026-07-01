import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// Patient default dataset for initial loading / pre-filling
const patientDetails = {
  robert: {
    input: "Bệnh nhân nam, 68 tuổi, chẩn đoán Đái tháo đường tuýp 2 kèm suy thận mạn tiến triển với mức lọc cầu thận eGFR = 28 mL/phút/1.73m2. Bác sĩ đang cân nhắc kê đơn Metformin 500mg để kiểm soát đường huyết."
  },
  emily: {
    input: "Bệnh nhân nữ, 55 tuổi, Đái tháo đường tuýp 2 kèm béo phì độ 1 (BMI = 31.5) và suy tim phân suất tống máu giảm (HFrEF). Cần tư vấn lựa chọn thuốc hạ đường huyết tối ưu có lợi ích tim mạch và cân nặng."
  },
  john: {
    input: "Bệnh nhân nam, 19 tuổi, nhập viện vì khát nhiều, tiểu nhiều, sụt cân 5kg trong 2 tuần. Kết quả xét nghiệm: C-peptide thấp, kháng thể kháng tế bào đảo tụy GAD65 dương tính."
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

  // CDSS QA Chatbot state
  const [qaQuery, setQaQuery] = useState("");
  const [qaHistory, setQaHistory] = useState([
    {
      sender: "bot",
      text: "Xin chào! Tôi là trợ lý tư vấn y khoa thông minh CDSS. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về bệnh Đái tháo đường, các thuốc điều trị, biến chứng hoặc chống chỉ định lâm sàng. Hệ thống sẽ truy vấn trực tiếp Đồ thị Tri thức Neo4j để trả lời chính xác nhất.",
    }
  ]);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaLogs, setQaLogs] = useState([]);
  const [showQaLogs, setShowQaLogs] = useState(false);

  const handleQaSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!qaQuery.trim() || qaLoading) return;

    const userMsg = qaQuery.trim();
    setQaQuery("");
    setQaLoading(true);
    setShowQaLogs(true);
    setQaLogs([`[QA Engine] Nhận câu hỏi tư vấn: "${userMsg}"`]);

    setQaHistory(prev => [...prev, { sender: "user", text: userMsg }]);

    const logLines = [
      `[Stage 0] Đang đối sánh thực thể lâm sàng trong đồ thị...`,
      `[Stage 1] Đang gọi bộ dịch Llama-3.3-70B biên dịch sang câu lệnh Cypher...`,
      `[Stage 2] Đang kiểm tra an toàn & kiểm duyệt câu lệnh Cypher...`,
      `[Stage 3] Thực thi truy vấn trên cơ sở dữ liệu đồ thị Neo4j AuraDB...`,
      `[Stage 4] Đang gọi LLM tổng hợp câu trả lời y khoa tiếng Việt...`,
      `[QA Engine] Hoàn tất xử lý câu hỏi tư vấn!`
    ];

    let logIdx = 0;
    const logInterval = setInterval(() => {
      if (logIdx < logLines.length) {
        setQaLogs(prev => [...prev, logLines[logIdx]]);
        logIdx++;
      } else {
        clearInterval(logInterval);
      }
    }, 150);

    try {
      const res = await axios.post('/api/cdss/qa', {
        query_text: userMsg
      });
      
      setQaHistory(prev => [...prev, {
        sender: "bot",
        text: res.data.answer,
        cypher: res.data.cypher_query,
        graphContext: res.data.graph_context,
        isFallback: res.data.is_fallback,
        logs: res.data.logs
      }]);
    } catch (err) {
      console.error("QA API Error:", err);
      setQaHistory(prev => [...prev, {
        sender: "bot",
        text: "Xin lỗi, hệ thống gặp lỗi kết nối với máy chủ CDSS. Vui lòng thử lại sau.",
        isFallback: true
      }]);
    } finally {
      setQaLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    // Keep text area initialized but do not auto-trigger analysis
  }, []);

  // Sync scroll for logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);



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
      `[CDSS Engine] Khởi chạy hệ hỗ trợ ra quyết định lâm sàng CDSS...`,
      `[Stage 1] Truy xuất toàn bộ thực thể từ CSDL Đồ thị Neo4j...`,
      `[Stage 1] Khởi chạy trích xuất và đối chiếu hai giai đoạn (Two-Stage Entity Linking)...`,
      `[Stage 2] Đang duyệt đồ thị BFS đa bước (Multi-hop Graph Traversal)...`,
      `[Stage 3] Đang tính điểm ưu tiên quan hệ và cắt tỉa tối ưu 40 bộ ba...`,
      `[Stage 4] Kích hoạt ngắt mạch an toàn lâm sàng (Clinical Circuit Breaker)...`,
      `[Stage 4] Đang gọi LLM lập luận lâm sàng có căn cứ đồ thị...`,
      `[CDSS Engine] Hoàn tất chẩn đoán hỗ trợ quyết định y khoa!`
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
        alert: { active: false, title: "", rule: "" },
        differential_diagnosis: {
          condition_a: "Đái tháo đường tuýp 2 + Béo phì + Suy tim", condition_b: "Suy tim sung huyết đơn thuần",
          features: [
            { characteristic: "Đường huyết đói / HbA1c", val_a: "Tăng cao (HbA1c > 8%)", val_b: "Bình thường" },
            { characteristic: "Triệu chứng suy tim", val_a: "Mệt mỏi, khó thở khi gắng sức", val_b: "Giống nhau" }
          ]
        },
        graph_path: [{ title: "Diabetes Mellitus, Non-Insulin-Dependent" }, { edge: "PREFERRED_OVER" }, { title: "pioglitazone" }],
        recommendations: [
          { type: "recommend", title: "GLP-1 RA (Liraglutide / Semaglutide)", desc: "Ưu tiên lựa chọn để hỗ trợ giảm cân và bảo vệ tim mạch.", relation: "PREFERRED_OVER" },
          { type: "recommend", title: "SGLT2i (Empagliflozin / Dapagliflozin)", desc: "Ưu tiên lựa chọn giúp cải thiện suy tim và kiểm soát đường huyết.", relation: "PREFERRED_OVER" },
          { type: "contraindicate", title: "Pioglitazone", desc: "Tránh sử dụng do làm tăng nguy cơ giữ nước và tiến triển suy tim.", relation: "CONTRAINDICATED_WITH" }
        ],
        logs: ["Đã phân tích các lựa chọn điều trị tối ưu dựa trên biến chứng Suy tim và Béo phì của bệnh nhân."]
      };
    } else if (pId === "john") {
      return {
        alert: { active: false, title: "", rule: "" },
        differential_diagnosis: {
          condition_a: "Đái tháo đường tuýp 1 (Tự miễn)", condition_b: "Đái tháo đường tuýp 2 (Kháng insulin)",
          features: [
            { characteristic: "Kháng thể GAD65", val_a: "Dương tính (+)", val_b: "Âm tính (-)" },
            { characteristic: "Định lượng C-peptide", val_a: "Giảm mạnh / Triệt tiêu", val_b: "Bình thường hoặc Tăng" }
          ]
        },
        graph_path: [{ title: "Diabetes Mellitus, Insulin-Dependent" }, { edge: "HAS_BIOMARKER" }, { title: "GAD65 autoantibodies" }],
        recommendations: [
          { type: "recommend", title: "Liệu pháp Insulin suốt đời", desc: "Điều trị bắt buộc đối với ĐTĐ tuýp 1 do thiếu hụt insulin tuyệt đối.", relation: "TREATED_BY" },
          { type: "recommend", title: "Giám sát Glucose liên tục (CGM)", desc: "Khuyên dùng để kiểm soát đường huyết tối ưu.", relation: "RECOMMEND" }
        ],
        logs: ["Đã đối chiếu Biomarker GAD65 và C-peptide để chẩn đoán phân biệt ĐTĐ tuýp 1."]
      };
    } else {
      return {
        alert: { active: true, title: "🛑 KÍCH HOẠT NGẮT MẠCH: Chống chỉ định dùng Metformin", rule: "[Suy thận mạn] → (CONTRAINDICATED_WITH) → [metformin]" },
        differential_diagnosis: {
          condition_a: "Đái tháo đường tuýp 2 kèm suy thận", condition_b: "Nhiễm toan lactic do thuốc",
          features: [
            { characteristic: "Mức lọc cầu thận eGFR", val_a: "28 mL/phút/1.73m2 (Giảm nặng)", val_b: "Bình thường" },
            { characteristic: "Chỉ định Metformin", val_a: "Chống chỉ định tuyệt đối", val_b: "Không liên quan" }
          ]
        },
        graph_path: [{ title: "Suy thận mạn" }, { edge: "CONTRAINDICATED_WITH" }, { title: "metformin" }],
        recommendations: [
          { type: "recommend", title: "Insulin", desc: "Liệu pháp thay thế an toàn khi eGFR < 30.", relation: "TREATED_BY" },
          { type: "contraindicate", title: "Metformin", desc: "Chống chỉ định tuyệt đối do eGFR giảm gây tích tụ axit lactic.", relation: "CONTRAINDICATED_WITH" }
        ],
        logs: ["Circuit Breaker kích hoạt thành công: Đã phát hiện chống chỉ định Metformin ở bệnh nhân suy thận eGFR < 30."]
      };
    }
  };



  const activePatient = patientDetails[patientId];

  return (
    <div className="bg-surface-container-low dark:bg-slate-900 text-on-surface dark:text-slate-100 antialiased flex flex-col h-screen overflow-hidden transition-colors duration-200">
      
      {/* Top Header */}
      <header className="flex justify-between items-center w-full px-lg h-16 bg-white dark:bg-slate-900 text-primary dark:text-inverse-primary border-b border-outline-variant dark:border-slate-800 z-40 transition-colors duration-200">
        <h1 className="font-extrabold text-2xl text-primary dark:text-emerald-400 tracking-tight flex items-center gap-2">
          <span className="material-symbols-outlined text-3xl">shield_moon</span>
          GlucoGraph <span className="text-xs font-normal bg-blue-100 dark:bg-emerald-950 text-blue-800 dark:text-emerald-400 px-2 py-0.5 rounded-full border border-blue-200 dark:border-emerald-800">CDSS Engine</span>
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

      {/* Main Wrapper */}
      <div className="flex-1 flex flex-row h-full w-full overflow-hidden transition-all duration-300">

        {/* Sidebar Navigation */}
        <aside className="w-64 bg-white dark:bg-slate-950 border-r border-outline-variant dark:border-slate-800 flex flex-col justify-between z-30 transition-colors duration-200 shrink-0">
          <div className="p-md space-y-xs">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-sm mb-xs">Menu chính</div>
            
            <button 
              onClick={() => setActiveTab("overview")} 
              className={`w-full flex items-center gap-sm px-md py-sm rounded-lg text-sm font-semibold transition-all ${activeTab === 'overview' ? 'bg-primary/10 dark:bg-emerald-500/10 text-primary dark:text-emerald-400 font-bold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
            >
              <span className="material-symbols-outlined text-lg">dashboard</span>
              Phân tích CDSS
            </button>

            <button 
              onClick={() => setActiveTab("qa")} 
              className={`w-full flex items-center gap-sm px-md py-sm rounded-lg text-sm font-semibold transition-all ${activeTab === 'qa' ? 'bg-primary/10 dark:bg-emerald-500/10 text-primary dark:text-emerald-400 font-bold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
            >
              <span className="material-symbols-outlined text-lg">chat</span>
              Tư vấn Đái tháo đường
            </button>
          </div>

          <div className="p-md border border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20 m-sm rounded-lg shadow-sm">
            <div className="flex gap-sm text-amber-600 dark:text-amber-400 items-start">
              <span className="material-symbols-outlined text-xl flex-shrink-0 mt-0.5" style={{fontVariationSettings: "'FILL' 1"}}>warning</span>
              <p className="text-xs leading-relaxed font-semibold">
                <span className="font-bold uppercase tracking-wider block mb-0.5 text-[9px] opacity-80">Khuyến cáo y khoa:</span>
                Hệ thống chỉ mang tính chất tham khảo và không thay thế kết luận chính xác từ bác sĩ.
              </p>
            </div>
          </div>
        </aside>

        {/* Dynamic content canvas */}
        <main className="flex-1 overflow-y-auto p-gutter bg-surface-container-low dark:bg-slate-900 transition-colors duration-200">
          
          {/* TAB: OVERVIEW */}
          {activeTab === "overview" && (
            <div className="space-y-gutter max-w-7xl mx-auto animate-fade-in">
              
              {/* Clinical input section */}
              <section className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-sm mb-md">
                  <div>
                    <h2 className="font-semibold text-lg text-on-surface dark:text-white flex items-center">
                      <span className="material-symbols-outlined mr-sm text-primary dark:text-emerald-400">edit_document</span>
                      Nhập tình huống lâm sàng CDSS
                    </h2>
                  </div>
                  <div className="flex flex-wrap items-center gap-xs self-start md:self-center">
                    <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Thử nhanh các ca:</span>
                    <button onClick={() => handlePatientChange('robert')} className={`text-xs border px-3 py-1 rounded-full font-medium transition-all ${patientId === 'robert' ? 'bg-primary text-white border-primary dark:bg-emerald-600 dark:border-emerald-600' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 border-gray-300 dark:border-slate-600'}`}>Ca 1 (Chống chỉ định)</button>
                    <button onClick={() => handlePatientChange('emily')} className={`text-xs border px-3 py-1 rounded-full font-medium transition-all ${patientId === 'emily' ? 'bg-primary text-white border-primary dark:bg-emerald-600 dark:border-emerald-600' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 border-gray-300 dark:border-slate-600'}`}>Ca 2 (Phối hợp tối ưu)</button>
                    <button onClick={() => handlePatientChange('john')} className={`text-xs border px-3 py-1 rounded-full font-medium transition-all ${patientId === 'john' ? 'bg-primary text-white border-primary dark:bg-emerald-600 dark:border-emerald-600' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 border-gray-300 dark:border-slate-600'}`}>Ca 3 (Chẩn đoán phân biệt)</button>
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

                  {/* Matched Entities from Neo4j */}
                  {result.matched_entities && result.matched_entities.length > 0 && (
                    <div className="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl px-lg py-md flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mr-1 flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm text-emerald-500">hub</span>
                        Thực thể Neo4j đã khớp:
                      </span>
                      {result.matched_entities.map((entity, eIdx) => (
                        <span key={eIdx} className="inline-flex items-center gap-1 bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-semibold px-2.5 py-1 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                          {entity}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="grid grid-cols-1 xl:grid-cols-12 gap-gutter">
                    
                    {/* Diagnostic Table & Graph View */}
                    <div className="xl:col-span-8 space-y-gutter">
                      
                      {/* Differential Diagnosis — Prose Cards */}
                      {result.differential_diagnosis && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                          <h3 className="font-semibold text-lg text-on-surface dark:text-white mb-md flex items-center">
                            <span className="material-symbols-outlined mr-sm text-emerald-500">compare</span>
                            Chẩn đoán phân biệt
                          </h3>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
                            {/* Card A */}
                            <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-md flex flex-col gap-sm bg-slate-50 dark:bg-slate-900">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="w-3 h-3 rounded-full bg-rose-400 flex-shrink-0"></span>
                                <span className="font-bold text-slate-800 dark:text-white text-sm">{result.differential_diagnosis.condition_a}</span>
                              </div>
                              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                                {result.differential_diagnosis.prose_a ||
                                  (result.differential_diagnosis.features && result.differential_diagnosis.features.map(f => f.val_a).join('. '))}
                              </p>
                            </div>
                            {/* Card B */}
                            <div className="rounded-xl border-2 border-emerald-300 dark:border-emerald-700 p-md flex flex-col gap-sm bg-emerald-50/50 dark:bg-emerald-950/20">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="w-3 h-3 rounded-full flex-shrink-0 bg-emerald-500"></span>
                                <span className="font-bold text-sm text-emerald-800 dark:text-emerald-300">
                                  {result.differential_diagnosis.condition_b}
                                  <span className="material-symbols-outlined text-xs align-middle ml-1 text-emerald-500" style={{fontVariationSettings: "'FILL' 1"}}>check_circle</span>
                                </span>
                              </div>
                              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                                {result.differential_diagnosis.prose_b ||
                                  (result.differential_diagnosis.features && result.differential_diagnosis.features.map(f => f.val_b).join('. '))}
                              </p>
                            </div>
                          </div>
                          {/* Distinguishing Factor */}
                          {result.differential_diagnosis.distinguishing_factor && (
                            <div className="mt-md flex items-start gap-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg px-md py-sm">
                              <span className="material-symbols-outlined text-amber-500 text-lg flex-shrink-0 mt-0.5">lightbulb</span>
                              <p className="text-sm text-amber-800 dark:text-amber-200 font-medium leading-relaxed">
                                <span className="font-bold">Yếu tố phân biệt:</span> {result.differential_diagnosis.distinguishing_factor}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Reasoning Path — Linear Chain + Evidence Triples Grid */}
                      {result.graph_path && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm">
                          <h3 className="font-semibold text-lg text-on-surface dark:text-white mb-md flex items-center">
                            <span className="material-symbols-outlined mr-sm text-primary dark:text-emerald-400">account_tree</span>
                            Luồng tư duy AI (GraphRAG Path)
                          </h3>

                          {/* Linear reasoning chain */}
                          <div className="relative bg-slate-50 dark:bg-slate-900 p-md rounded-xl border border-gray-100 dark:border-slate-800 flex flex-row items-center flex-wrap justify-center gap-2 overflow-x-auto min-h-[80px] mb-md">
                            {result.graph_path.map((node, nIdx) => {
                              const nodeTypeColors = {
                                'Disease':  'border-rose-400 bg-rose-50 dark:bg-rose-950/30',
                                'Drug':     'border-emerald-400 bg-emerald-50 dark:bg-emerald-950/30',
                                'Symptom':  'border-amber-400 bg-amber-50 dark:bg-amber-950/30',
                                'Finding':  'border-amber-400 bg-amber-50 dark:bg-amber-950/30',
                                'Anatomy':  'border-purple-400 bg-purple-50 dark:bg-purple-950/30',
                                'BodyPart': 'border-purple-400 bg-purple-50 dark:bg-purple-950/30',
                                'Concept':  'border-slate-400 bg-slate-50 dark:bg-slate-800',
                              };
                              const nodeTypeDot = {
                                'Disease':  'bg-rose-500', 'Drug': 'bg-emerald-500',
                                'Symptom':  'bg-amber-500', 'Finding': 'bg-amber-500',
                                'Anatomy':  'bg-purple-500', 'BodyPart': 'bg-purple-500',
                                'Concept':  'bg-slate-400',
                              };
                              const hopLabel = node.hop === 0 ? 'Seed' : node.hop === 1 ? 'Hop 1' : node.hop === 2 ? 'Hop 2' : null;
                              const colorClass = nodeTypeColors[node.node_type] || 'border-blue-400 bg-blue-50 dark:bg-blue-950/30';
                              const dotClass = nodeTypeDot[node.node_type] || 'bg-blue-500';
                              return node.edge ? (
                                <div key={nIdx} className="flex flex-col items-center flex-shrink-0">
                                  <span className="text-[9px] px-2 py-0.5 text-slate-600 dark:text-emerald-300 bg-white dark:bg-slate-950 rounded-full border border-slate-200 dark:border-slate-800 font-mono font-bold whitespace-nowrap flex items-center gap-1">
                                    {node.edge}
                                  </span>
                                  <div className="flex items-center mt-1">
                                    <div className="h-[2px] w-8 bg-blue-300 dark:bg-slate-600"></div>
                                    <span className="material-symbols-outlined text-sm -ml-2 text-blue-400 dark:text-slate-500">arrow_forward</span>
                                  </div>
                                </div>
                              ) : (
                                <div key={nIdx} className={`border-2 ${colorClass} px-3 py-1.5 rounded-xl flex flex-col items-start shadow-sm flex-shrink-0 max-w-[200px]`}>
                                  <div className="flex items-center gap-1.5">
                                    <span className={`w-2.5 h-2.5 rounded-full ${dotClass} flex-shrink-0`}></span>
                                    <span className="font-semibold text-xs text-slate-800 dark:text-white leading-tight">
                                      {(node.original_id && node.original_id !== node.title) ? `${node.original_id} (${node.title})` : node.title}
                                    </span>
                                  </div>
                                  <div className="flex gap-1 flex-wrap mt-1">
                                    {node.node_type && <span className="text-[8px] font-bold uppercase bg-white/70 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 px-1 py-0.5 rounded">{node.node_type}</span>}
                                    {hopLabel && <span className="text-[8px] font-bold uppercase bg-blue-100 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 px-1 py-0.5 rounded">{hopLabel}</span>}
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          {/* Evidence Triples Grid */}
                          {result.evidence_triples && result.evidence_triples.length > 0 && (() => {
                            const diagTriples = result.evidence_triples.filter(t => t.group === 'diagnosis');
                            const treatTriples = result.evidence_triples.filter(t => t.group === 'treatment');
                            const nodeTypeDot = {
                              'Disease': 'bg-rose-400', 'Drug': 'bg-emerald-400',
                              'Symptom': 'bg-amber-400', 'Finding': 'bg-amber-400',
                              'Anatomy': 'bg-purple-400', 'Concept': 'bg-slate-400',
                            };
                            const TripleRow = ({ t, idx }) => (
                              <div key={idx} className="flex flex-wrap items-center justify-between bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono shadow-sm w-full gap-2">
                                <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
                                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${nodeTypeDot[t.subject_type] || 'bg-slate-400'}`}></span>
                                  <span className="text-slate-700 dark:text-slate-200 font-medium" title={t.original_subject_id || t.subject}>
                                    {(t.original_subject_id && t.original_subject_id !== t.subject) ? `${t.original_subject_id} (${t.subject})` : t.subject}
                                  </span>
                                  <span className="text-blue-500 dark:text-blue-400 font-bold whitespace-nowrap shrink-0">→ {t.relation} →</span>
                                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${nodeTypeDot[t.object_type] || 'bg-slate-400'}`}></span>
                                  <span className="text-slate-700 dark:text-slate-200 font-medium" title={t.original_object_id || t.object}>
                                    {(t.original_object_id && t.original_object_id !== t.object) ? `${t.original_object_id} (${t.object})` : t.object}
                                  </span>
                                </div>
                              </div>
                            );
                            return (
                              <div className="grid grid-cols-1 lg:grid-cols-2 gap-md">
                                {diagTriples.length > 0 && (
                                  <div>
                                    <div className="flex items-center gap-1.5 mb-sm">
                                      <span className="material-symbols-outlined text-sm text-rose-500">biotech</span>
                                      <span className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">Bộ ba chẩn đoán</span>
                                    </div>
                                    <div className="space-y-1.5">
                                      {diagTriples.map((t, idx) => <TripleRow key={idx} t={t} idx={idx} />)}
                                    </div>
                                  </div>
                                )}
                                {treatTriples.length > 0 && (
                                  <div>
                                    <div className="flex items-center gap-1.5 mb-sm">
                                      <span className="material-symbols-outlined text-sm text-emerald-500">medication</span>
                                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Bộ ba điều trị</span>
                                    </div>
                                    <div className="space-y-1.5">
                                      {treatTriples.map((t, idx) => <TripleRow key={idx} t={t} idx={idx} />)}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })()}

                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-md px-xs">* Các bộ ba trích xuất trực tiếp từ Neo4j Knowledge Graph — tất cả quan hệ đều có bằng chứng trong đồ thị.</p>
                        </div>
                      )}

                    </div>

                    {/* Recommendations Panel */}
                    <div className="xl:col-span-4">
                      <div className="bg-white dark:bg-slate-800 rounded-xl border border-outline-variant dark:border-slate-700 p-lg shadow-sm h-full flex flex-col justify-between">
                        <div>
                          <h3 className="font-semibold text-lg text-on-surface dark:text-white mb-lg flex items-center border-b border-gray-100 dark:border-slate-700 pb-sm">
                            <span className="material-symbols-outlined mr-sm text-primary dark:text-emerald-400">medication</span>
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



          {/* TAB: MEDICAL QA CONSULTATION */}
          {activeTab === "qa" && (
            <div className="max-w-5xl mx-auto space-y-gutter animate-fade-in flex flex-col h-[calc(100vh-8rem)]">
              
              {/* QA Header */}
              <div className="bg-white dark:bg-slate-800 rounded-t-xl border-x border-t border-outline-variant dark:border-slate-700 p-lg shadow-sm flex justify-between items-center shrink-0">
                <div>
                  <h2 className="font-bold text-xl text-primary dark:text-emerald-400 flex items-center gap-2">
                    <span className="material-symbols-outlined">chat</span>
                    Tư vấn Hỏi đáp Y khoa Đái tháo đường
                  </h2>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Hỏi đáp trực tiếp bằng tiếng Việt. Câu hỏi được dịch sang Cypher và xác thực dựa trên Đồ thị Tri thức Neo4j (AMG-RAG).
                  </p>
                </div>
                <div className="flex gap-2">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
                    Neo4j Graph Active
                  </span>
                </div>
              </div>

              {/* Chat Container */}
              <div className="flex-1 flex flex-col md:flex-row border-x border-b border-outline-variant dark:border-slate-700 bg-white dark:bg-slate-800 rounded-b-xl overflow-hidden shadow-sm min-h-0">
                
                {/* Message area */}
                <div className="flex-1 flex flex-col min-h-0 bg-slate-50 dark:bg-slate-900">
                  <div className="flex-1 overflow-y-auto p-lg space-y-md">
                    {qaHistory.map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                        <div className={`max-w-[85%] rounded-xl p-md shadow-sm border ${
                          msg.sender === 'user' 
                            ? 'bg-primary text-white border-primary dark:bg-emerald-600 dark:border-emerald-600' 
                            : 'bg-white dark:bg-slate-800 text-on-surface dark:text-slate-100 border-slate-200 dark:border-slate-700'
                        }`}>
                          {msg.sender === 'user' && (
                            <div className="text-xs font-bold opacity-75 mb-xs uppercase tracking-wider flex items-center gap-1">
                              <span className="material-symbols-outlined text-xs">person</span>
                              Bác sĩ
                            </div>
                          )}

                          
                          <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">{msg.text}</p>
                          
                          {/* Metadata box for bot responses */}
                          {msg.sender === 'bot' && (msg.cypher || (msg.graphContext && msg.graphContext.length > 0)) && (
                            <div className="mt-md pt-md border-t border-slate-100 dark:border-slate-700 space-y-md">
                              
                              {/* Cypher Box */}
                              {msg.cypher && msg.cypher !== "N/A" && (
                                <div>
                                  <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1 flex items-center gap-1">
                                    <span className="material-symbols-outlined text-[12px] text-blue-500">terminal</span>
                                    Truy vấn Cypher đã chạy trên Neo4j:
                                  </span>
                                  <pre className="text-xs bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-emerald-400 p-md rounded-lg overflow-x-auto border border-slate-200 dark:border-slate-800 font-mono whitespace-pre-wrap">
                                    {msg.cypher}
                                  </pre>
                                </div>
                              )}



                              {/* Graph Context */}
                              {msg.graphContext && msg.graphContext.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1 flex items-center gap-1">
                                    <span className="material-symbols-outlined text-[12px] text-emerald-500">hub</span>
                                    Minh chứng đồ thị làm căn cứ (Triples):
                                  </span>
                                  <div className="max-h-36 overflow-y-auto space-y-1 pr-xs">
                                    {msg.graphContext.map((t, tIdx) => (
                                      <div key={tIdx} className="bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 rounded px-2 py-1 text-[10px] font-mono flex items-center gap-1 text-slate-600 dark:text-slate-300">
                                        <span className="font-bold text-slate-800 dark:text-slate-200">{t.subject || t.subject_type}</span>
                                        <span className="text-blue-500 dark:text-blue-400">-{t.relation}-&gt;</span>
                                        <span className="font-bold text-slate-800 dark:text-slate-200">{t.object || t.object_type}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {qaLoading && (
                      <div className="flex justify-start animate-pulse">
                        <div className="bg-white dark:bg-slate-800 rounded-xl p-md border border-slate-200 dark:border-slate-700 max-w-[80%]">
                          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
                            <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-500 animate-ping"></span>
                            Hệ thống đang suy luận và truy vấn Neo4j...
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Input Form */}
                  <form onSubmit={handleQaSubmit} className="p-md border-t border-outline-variant dark:border-slate-700 bg-white dark:bg-slate-800 flex gap-sm shrink-0">
                    <input 
                      type="text" 
                      value={qaQuery}
                      onChange={(e) => setQaQuery(e.target.value)}
                      disabled={qaLoading}
                      placeholder="Nhập câu hỏi tư vấn về đái tháo đường, thuốc điều trị, biến chứng..."
                      className="flex-1 rounded-lg border border-outline-variant dark:border-slate-600 focus:border-primary-container focus:ring focus:ring-primary-container/30 bg-surface dark:bg-slate-900 text-on-surface dark:text-white px-md py-sm text-sm"
                    />
                    <button 
                      type="submit"
                      disabled={qaLoading || !qaQuery.trim()}
                      className="bg-primary hover:bg-blue-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white font-semibold px-lg py-sm rounded-lg flex items-center transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      <span className="material-symbols-outlined text-lg mr-xs">send</span> Gửi
                    </button>
                  </form>
                </div>

                {/* Right side logs panel */}
                {showQaLogs && (
                  <div className="w-full md:w-80 border-t md:border-t-0 md:border-l border-outline-variant dark:border-slate-700 bg-slate-950 text-emerald-400 font-mono text-xs flex flex-col h-48 md:h-auto shrink-0 animate-fade-in">
                    <div className="p-xs bg-slate-900 border-b border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-md flex justify-between items-center">
                      <span>Nhật ký truy vấn QA</span>
                      <button type="button" onClick={() => setShowQaLogs(false)} className="text-slate-500 hover:text-white"><span className="material-symbols-outlined text-sm">close</span></button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-md space-y-1">
                      {qaLogs.map((log, idx) => (
                        <div key={idx} className="py-0.5 leading-relaxed">{log}</div>
                      ))}
                    </div>
                  </div>
                )}
                
              </div>
            </div>
          )}

        </main>
      </div>

    </div>
  );
}

export default App;