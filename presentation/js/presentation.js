/**
 * MentorMind — Denso Hackathon Interactive Presentation Controller
 * Supports: keyboard navigation, overview grid, presenter notes, pitch timer, 
 * interactive slide tabs, and fullscreen mode.
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentSlideIndex = 0;
  const slides = Array.from(document.querySelectorAll('.slide'));
  const totalSlides = slides.length;

  // Elements
  const currentSlideNumEl = document.getElementById('currentSlideNum');
  const totalSlidesNumEl = document.getElementById('totalSlidesNum');
  const progressFillEl = document.getElementById('progressFill');
  const slideDotsContainer = document.getElementById('slideDots');
  const btnPrev = document.getElementById('btnPrev');
  const btnNext = document.getElementById('btnNext');
  
  // Toggles & Modals
  const btnOverview = document.getElementById('btnOverview');
  const btnNotes = document.getElementById('btnNotes');
  const btnHelp = document.getElementById('btnHelp');
  const btnFullscreen = document.getElementById('btnFullscreen');
  
  const overviewModal = document.getElementById('overviewModal');
  const helpModal = document.getElementById('helpModal');
  const lightboxModal = document.getElementById('lightboxModal');
  const notesDrawer = document.getElementById('notesDrawer');
  const notesContent = document.getElementById('notesContent');
  
  // Pitch Timer
  const pitchTimerEl = document.getElementById('pitchTimer');
  const timerTextEl = document.getElementById('timerText');
  let timerSeconds = 300; // 5 minutes countdown
  let timerInterval = null;
  let timerRunning = false;

  // Presenter Notes Database
  const presenterNotesData = [
    {
      slide: 1,
      title: "Slide 1: Mở đầu & Đặt vấn đề",
      time: "Khuyến nghị: 30s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Gây ấn tượng ngay lập tức về tầm vóc của đề tài và định vị giải pháp MentorMind cho Denso Hackathon.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Kính chào Ban giám khảo Denso! Chúng tôi mang đến <strong>MentorMind</strong> — giải pháp số hóa bí quyết chuyên gia (Master Know-How) cho AI học tập.</li>
          <li>Khác với cách số hóa truyền thống đòi hỏi viết tài liệu thủ công hàng trăm trang, MentorMind <em>tự động capture quy trình từ thao tác thực tế và lời bình luận tự nhiên</em>.</li>
          <li>Hôm nay, chúng tôi sẽ trình bày qua 4 phần: Bối cảnh, Đề bài, Bài học quốc tế, và Giải pháp kiến trúc của đội.</li>
        </ul>
      `
    },
    {
      slide: 2,
      title: "Slide 2: Bối cảnh & Điểm đau nhức nhối",
      time: "Khuyến nghị: 45s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Làm nổi bật mức độ khẩn cấp của vấn đề thất thoát bí quyết trong nhà máy sản xuất linh kiện ô tô.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Tại sao đề tài này lại cấp bách với Denso? Làn sóng thợ lành nghề (master artisans) nghỉ hưu đang mang theo hàng chục năm kinh nghiệm quý báu mà chưa từng được viết ra giấy.</li>
          <li>SOP và tài liệu chữ viết tay không thể theo kịp độ biến thiên và vi thao tác tinh tế tại xưởng.</li>
          <li>Trong sản xuất ô tô, một sai lệch nhỏ góc đặt linh kiện sẽ gây ra lỗi dây chuyền (defect propagation) ảnh hưởng đến toàn bộ lô hàng.</li>
          <li>Đây chính là cơ hội vàng cho Multimodal VLM và GraphRAG.</li>
        </ul>
      `
    },
    {
      slide: 3,
      title: "Slide 3: Đề bài & 4 Deliverables",
      time: "Khuyến nghị: 45s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Khẳng định sự hiểu sâu sắc đề bài và cam kết 4 sản phẩm cụ thể sau 3 tháng.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Đề bài: Thu thập workflow và tư duy suy luận của chuyên gia vào Knowledge Base, dùng LLM tái sử dụng cho tác vụ tương tự.</li>
          <li>Cam kết 4 Deliverables rõ ràng:
            <ol>
              <li><strong>Standardized Template:</strong> Schema WorkProfile JSON chuẩn hóa từng step, lý do, ngoại lệ.</li>
              <li><strong>Knowledge Base:</strong> Hybrid GraphRAG (Neo4j kết hợp PGVector).</li>
              <li><strong>Dual AI Agents:</strong> Work Assistant tại trạm + RCA Agent truy vết lỗi.</li>
              <li><strong>Evaluation Report:</strong> Đánh giá định lượng với Ragas framework.</li>
            </ol>
          </li>
        </ul>
      `
    },
    {
      slide: 4,
      title: "Slide 4: Case Tham Khảo & Góc Nhìn Đạo Đức",
      time: "Khuyến nghị: 45s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Tạo sự khác biệt tư duy: Phân tích case study thực tế quốc tế để thấy rủi ro nếu làm AI sai cách.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Chúng tôi phân tích bài học từ phóng sự điều tra về công nhân Ấn Độ đeo camera gắn đầu suốt ca làm việc.</li>
          <li>Doanh nghiệp âm thầm lấy dữ liệu vận động tinh giá rẻ để huấn luyện robot thay thế chính họ.</li>
          <li>Hệ quả: Sự chống đối ngầm, giấu nghề, và khủng hoảng niềm tin đạo đức.</li>
          <li>Nếu một giải pháp AI khiến chuyên gia cảm thấy bị khai thác và thay thế, giải pháp đó sẽ thất bại ngay tại xưởng sản xuất!</li>
        </ul>
      `
    },
    {
      slide: 5,
      title: "Slide 5: Bài Học & Hai Hướng Đi Đối Lập",
      time: "Khuyến nghị: 45s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Khắc sâu triết lý của MentorMind: "Capture & Empower" thay vì "Extract & Replace".</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Bảng so sánh này là linh hồn của MentorMind:
            <ul>
              <li><strong>Extract & Replace:</strong> Chuyên gia bị động, không lợi ích, dẫn tới mất niềm tin.</li>
              <li><strong>Capture & Empower (MentorMind):</strong> Chuyên gia là trung tâm, chủ động giải thích, được vinh danh và nhận benefit ghi nhận.</li>
            </ul>
          </li>
          <li>Chuyên gia không sợ bị mất việc, mà tự hào vì bí quyết của mình được kế thừa và tên tuổi được trích dẫn trên mọi câu trả lời của AI.</li>
        </ul>
      `
    },
    {
      slide: 6,
      title: "Slide 6: Quy Trình Giải Pháp 4 Bước",
      time: "Khuyến nghị: 45s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Trình bày luồng hoạt động mượt mà từ camera tại trạm tới trợ lý AI.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li><strong>Bước 1 - Capture:</strong> Camera trạm ghi lại thao tác 3–5 phút tự nhiên, không đổi nhịp dây chuyền.</li>
          <li><strong>Bước 2 - Giải thích:</strong> Chuyên gia dừng lại 30s giải thích *vì sao* làm như vậy -> nhận điểm benefit.</li>
          <li><strong>Bước 3 - Xử lý AI:</strong> VLM 3 lượt (Qwen3-VL) + Docling OCR sinh hồ sơ công đoạn tự động. Chuyên gia chỉ bấm Duyệt!</li>
          <li><strong>Bước 4 - Lưu trữ & Kích hoạt:</strong> Nạp vào GraphRAG + Vector, kết nối dữ liệu lỗi Sigma MES.</li>
        </ul>
      `
    },
    {
      slide: 7,
      title: "Slide 7: Kiến Trúc Kỹ Thuật 5 Lớp",
      time: "Khuyến nghị: 60s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Chứng minh năng lực kỹ thuật vững chắc: self-hosted VLM, GraphRAG, dual agents, Ragas.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Kiến trúc 5 lớp hoàn chỉnh:
            <ul>
              <li><strong>Lớp 1: Ingestion:</strong> Video 4–8 fps, audio, bản vẽ kỹ thuật PDF/DOCX (Docling).</li>
              <li><strong>Lớp 2: Multimodal VLM:</strong> Qwen3-VL-8B self-hosted bảo mật dữ liệu tuyệt đối + MediaPipe Hands.</li>
              <li><strong>Lớp 3: Knowledge Base:</strong> PostgreSQL pgvector (RRF dense+lexical) + Neo4j GraphRAG + Sigma MES Adapter.</li>
              <li><strong>Lớp 4: Dual Agents:</strong> Work Assistant (trả lời có citation & refusal guard) và RCA Agent (5-Why).</li>
              <li><strong>Lớp 5: Evaluation:</strong> Ragas framework tự động chấm Faithfulness ≥ 0.85.</li>
            </ul>
          </li>
        </ul>
      `
    },
    {
      slide: 8,
      title: "Slide 8: Roadmap & Thông Điệp Kết",
      time: "Khuyến nghị: 30s",
      notes: `
        <h4>Mục tiêu:</h4>
        <p>Chốt lại bài thuyết trình với kế hoạch thực thi khả thi và thông điệp truyền cảm hứng mạnh mẽ.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Lộ trình 3 tháng rõ ràng: Tháng 1 hoàn thiện Capture & Template; Tháng 2 hoàn tất Knowledge Base & Agents; Tháng 3 đánh giá Ragas & Pilot tại trạm kitting/packing Denso.</li>
          <li>Chúng tôi kết thúc với tôn chỉ: <em>"Giữ lại tri thức — Trao quyền cho con người, không thay thế con người."</em></li>
          <li>Xin chân thành cảm ơn Ban giám khảo, MentorMind sẵn sàng cho phần Q&A!</li>
        </ul>
      `
    }
  ];

  // Initialize Slide Dots
  function initDots() {
    slideDotsContainer.innerHTML = '';
    slides.forEach((_, idx) => {
      const dot = document.createElement('button');
      dot.className = `slide-dot ${idx === 0 ? 'active' : ''}`;
      dot.title = `Chuyển tới slide ${idx + 1}`;
      dot.setAttribute('aria-label', `Slide ${idx + 1}`);
      dot.addEventListener('click', () => goToSlide(idx));
      slideDotsContainer.appendChild(dot);
    });
  }

  // Update Slide View
  function goToSlide(index) {
    if (index < 0 || index >= totalSlides) return;

    slides.forEach((slide, idx) => {
      slide.classList.remove('active', 'prev');
      if (idx === index) {
        slide.classList.add('active');
      } else if (idx < index) {
        slide.classList.add('prev');
      }
    });

    currentSlideIndex = index;
    updateUI();
  }

  function nextSlide() {
    if (currentSlideIndex < totalSlides - 1) {
      goToSlide(currentSlideIndex + 1);
    }
  }

  function prevSlide() {
    if (currentSlideIndex > 0) {
      goToSlide(currentSlideIndex - 1);
    }
  }

  // Update Navigation UI & Indicators
  function updateUI() {
    const slideNumber = currentSlideIndex + 1;
    currentSlideNumEl.textContent = String(slideNumber).padStart(2, '0');
    totalSlidesNumEl.textContent = String(totalSlides).padStart(2, '0');

    // Progress bar
    const progressPercent = ((currentSlideIndex + 1) / totalSlides) * 100;
    progressFillEl.style.width = `${progressPercent}%`;

    // Dots
    const dots = slideDotsContainer.querySelectorAll('.slide-dot');
    dots.forEach((dot, idx) => {
      dot.classList.toggle('active', idx === currentSlideIndex);
    });

    // Nav Buttons
    btnPrev.disabled = currentSlideIndex === 0;
    btnNext.disabled = currentSlideIndex === totalSlides - 1;

    // Update Presenter Notes
    updatePresenterNotes(currentSlideIndex);

    // Update Overview Thumbnails Active State
    const thumbs = document.querySelectorAll('.overview-thumb');
    thumbs.forEach((thumb, idx) => {
      thumb.classList.toggle('active', idx === currentSlideIndex);
    });
  }

  // Presenter Notes Update
  function updatePresenterNotes(slideIdx) {
    const note = presenterNotesData[slideIdx];
    if (note && notesContent) {
      notesContent.innerHTML = `
        <div class="time-guidance">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          ${note.time}
        </div>
        ${note.notes}
      `;
    }
  }

  // Build Overview Bento Grid
  function buildOverviewGrid() {
    const grid = document.getElementById('overviewGrid');
    if (!grid) return;
    grid.innerHTML = '';

    slides.forEach((slide, idx) => {
      const titleEl = slide.querySelector('.slide-title') || slide.querySelector('.hero-title');
      const title = titleEl ? titleEl.textContent.trim().replace(/\s+/g, ' ').substring(0, 48) : `Slide ${idx + 1}`;
      const catEl = slide.querySelector('.slide-category') || slide.querySelector('.hero-tag');
      const cat = catEl ? catEl.textContent.trim() : 'PHẦN ' + (idx + 1);

      const thumb = document.createElement('div');
      thumb.className = `overview-thumb ${idx === currentSlideIndex ? 'active' : ''}`;
      thumb.innerHTML = `
        <span class="thumb-idx">${cat} · 0${idx + 1}</span>
        <h4 class="thumb-title">${title}</h4>
        <span class="thumb-desc">Bấm để chuyển tới slide</span>
      `;
      thumb.addEventListener('click', () => {
        goToSlide(idx);
        toggleOverviewModal(false);
      });
      grid.appendChild(thumb);
    });
  }

  // Modals & Drawers Toggles
  function toggleOverviewModal(show) {
    const isOpen = show !== undefined ? show : !overviewModal.classList.contains('open');
    overviewModal.classList.toggle('open', isOpen);
    btnOverview.classList.toggle('active', isOpen);
  }

  function toggleHelpModal(show) {
    const isOpen = show !== undefined ? show : !helpModal.classList.contains('open');
    helpModal.classList.toggle('open', isOpen);
    btnHelp.classList.toggle('active', isOpen);
  }

  function toggleLightboxModal(show) {
    const isOpen = show !== undefined ? show : !lightboxModal.classList.contains('open');
    lightboxModal.classList.toggle('open', isOpen);
  }

  function toggleNotesDrawer(show) {
    const isOpen = show !== undefined ? show : !notesDrawer.classList.contains('open');
    notesDrawer.classList.toggle('open', isOpen);
    btnNotes.classList.toggle('active', isOpen);
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => {
        console.warn(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  }

  // Pitch Timer (5-minute rehearse)
  function togglePitchTimer() {
    if (timerRunning) {
      clearInterval(timerInterval);
      timerRunning = false;
      pitchTimerEl.classList.remove('running');
    } else {
      timerRunning = true;
      pitchTimerEl.classList.add('running');
      timerInterval = setInterval(() => {
        if (timerSeconds > 0) {
          timerSeconds--;
          updateTimerDisplay();
        } else {
          clearInterval(timerInterval);
          timerRunning = false;
        }
      }, 1000);
    }
  }

  function updateTimerDisplay() {
    const mins = Math.floor(timerSeconds / 60);
    const secs = timerSeconds % 60;
    timerTextEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    if (timerSeconds <= 60 && timerSeconds > 0) {
      pitchTimerEl.classList.add('danger');
      pitchTimerEl.classList.remove('warning');
    } else if (timerSeconds <= 120) {
      pitchTimerEl.classList.add('warning');
      pitchTimerEl.classList.remove('danger');
    } else {
      pitchTimerEl.classList.remove('warning', 'danger');
    }
  }

  // Event Listeners for Nav
  btnPrev.addEventListener('click', prevSlide);
  btnNext.addEventListener('click', nextSlide);
  btnOverview.addEventListener('click', () => toggleOverviewModal());
  btnNotes.addEventListener('click', () => toggleNotesDrawer());
  btnHelp.addEventListener('click', () => toggleHelpModal());
  btnFullscreen.addEventListener('click', toggleFullscreen);
  pitchTimerEl.addEventListener('click', togglePitchTimer);

  // Close buttons for modals
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      toggleOverviewModal(false);
      toggleHelpModal(false);
      toggleLightboxModal(false);
    });
  });

  document.getElementById('closeNotesBtn').addEventListener('click', () => {
    toggleNotesDrawer(false);
  });

  // Lightbox Trigger from Slide 7
  const viewDiagramBtn = document.getElementById('btnViewDiagram');
  if (viewDiagramBtn) {
    viewDiagramBtn.addEventListener('click', () => toggleLightboxModal(true));
  }

  // Interactive Layer Inspector on Slide 7
  const layersData = [
    {
      name: "Lớp 1: Thu thập & Capture",
      tag: "MULTIMODAL INGESTION",
      desc: "Ghi nhận dữ liệu thực tế tại trạm làm việc mà không làm gián đoạn dây chuyền:",
      details: [
        "Camera tại trạm: Quay video thao tác 4–8 fps (ưu tiên lấy mẫu cử động tay nhanh)",
        "Micro bình luận: Thu âm lời giải thích của chuyên gia khi thao tác",
        "Docling / mmore: Trích xuất có cấu trúc bản vẽ kỹ thuật, tiêu chuẩn lắp ráp PDF/DOCX"
      ]
    },
    {
      name: "Lớp 2: Xử lý Đa phương thức VLM",
      tag: "VLM PIPELINE 3 LƯỢT",
      desc: "Chuyển video và lời nói thành WorkProfile có cấu trúc thông qua pipeline 3 lượt:",
      details: [
        "Lượt 1 - Phân đoạn: MediaPipe Hands xác định ranh giới và nhịp cử động tay",
        "Lượt 2 - Mô tả chi tiết: Qwen3-VL-8B (self-hosted BF16) sinh mô tả step, key_point, reason",
        "Lượt 3 - Tổng hợp Task Graph: Kiểm tra mâu thuẫn, đảm bảo schema trước khi chuyên gia duyệt"
      ]
    },
    {
      name: "Lớp 3: Knowledge Base Hybrid",
      tag: "GRAPHRAG & PGVECTOR",
      desc: "Lưu trữ tri thức với sự kết hợp hoàn hảo giữa đồ thị và vector:",
      details: [
        "Neo4j Knowledge Graph: Mô hình hóa Equipment –has→ Symptom –caused_by→ RootCause –fixed_by→ Procedure",
        "PostgreSQL + pgvector: Tìm kiếm ngữ nghĩa lai Dense HNSW + Lexical full-text gộp bằng Reciprocal Rank Fusion (RRF)",
        "Sigma MES Adapter: Liên kết hồ sơ công đoạn với mã lô hàng, sản phẩm, và lịch sử lỗi thực tế"
      ]
    },
    {
      name: "Lớp 4: Dual AI Agents",
      tag: "SPECIALIZED AGENTS",
      desc: "Hai agent chuyên biệt phục vụ hai nhóm người dùng tại xưởng:",
      details: [
        "Work Assistant: Trợ lý hỏi-đáp công đoạn cho thợ mới, bắt buộc trích dẫn nguồn (citation) và cơ chế từ chối khi không chắc chắn",
        "RCA Agent: Hỗ trợ tổ trưởng điều tra 5-Why tìm nguyên nhân gốc rễ, đối chiếu ca sự cố tương tự và xuất bản nháp báo cáo A3/8D"
      ]
    },
    {
      name: "Lớp 5: Đánh giá & Ragas",
      tag: "CONTINUOUS EVALUATION",
      desc: "Kiểm định khoa học và đo lường hiệu quả nghiệp vụ thực tế:",
      details: [
        "Ragas Quality Benchmark: Đạt Faithfulness ≥ 0.85, Answer Relevancy ≥ 0.80 trên bộ golden test",
        "A/B Testing tại xưởng: Đo lường mức giảm thời gian giải quyết sự cố và tỷ lệ lắp ráp chuẩn xác lần đầu của thợ mới"
      ]
    }
  ];

  const layerRows = document.querySelectorAll('.layer-row');
  const inspectorTag = document.getElementById('inspectorTag');
  const inspectorTitle = document.getElementById('inspectorTitle');
  const inspectorBody = document.getElementById('inspectorBody');

  layerRows.forEach((row, idx) => {
    row.addEventListener('click', () => {
      layerRows.forEach(r => r.classList.remove('active'));
      row.classList.add('active');

      const data = layersData[idx];
      if (data && inspectorTag && inspectorTitle && inspectorBody) {
        inspectorTag.textContent = data.tag;
        inspectorTitle.textContent = data.name;
        inspectorBody.innerHTML = `
          <p>${data.desc}</p>
          <ul>
            ${data.details.map(d => `<li>${d}</li>`).join('')}
          </ul>
        `;
      }
    });
  });

  // Interactive Step Cards on Slide 6
  const stepCards = document.querySelectorAll('.step-card');
  stepCards.forEach(card => {
    card.addEventListener('click', () => {
      stepCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
    });
  });

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    // Ignore keydown if input or textarea is active
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    switch (e.key) {
      case 'ArrowRight':
      case ' ':
      case 'PageDown':
      case 'Enter':
      case 'l':
      case 'L':
        e.preventDefault();
        nextSlide();
        break;

      case 'ArrowLeft':
      case 'Backspace':
      case 'PageUp':
      case 'h':
      case 'H':
        e.preventDefault();
        prevSlide();
        break;

      case 'Home':
        e.preventDefault();
        goToSlide(0);
        break;

      case 'End':
        e.preventDefault();
        goToSlide(totalSlides - 1);
        break;

      case 'f':
      case 'F':
        e.preventDefault();
        toggleFullscreen();
        break;

      case 'o':
      case 'O':
      case 'm':
      case 'M':
        e.preventDefault();
        toggleOverviewModal();
        break;

      case 'n':
      case 'N':
        e.preventDefault();
        toggleNotesDrawer();
        break;

      case 't':
      case 'T':
        e.preventDefault();
        togglePitchTimer();
        break;

      case '?':
      case 'k':
      case 'K':
        e.preventDefault();
        toggleHelpModal();
        break;

      case 'Escape':
        toggleOverviewModal(false);
        toggleHelpModal(false);
        toggleLightboxModal(false);
        toggleNotesDrawer(false);
        break;
    }
  });

  // Touch Swipe for Mobile / Tablet Presentation
  let touchStartX = 0;
  let touchEndX = 0;

  document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });

  document.addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
  }, { passive: true });

  function handleSwipe() {
    const diff = touchEndX - touchStartX;
    if (Math.abs(diff) > 50) {
      if (diff < 0) {
        nextSlide();
      } else {
        prevSlide();
      }
    }
  }

  // Initialize
  initDots();
  buildOverviewGrid();
  updateUI();
});
