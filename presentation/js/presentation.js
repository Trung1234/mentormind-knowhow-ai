/**
 * MentorMind — Denso Hackathon Interactive Presentation Controller (Vietnamese Edition)
 * Features: Keyboard navigation, 8-slide overview grid, presenter notes, pitch timer, 
 * interactive layer inspector, and fullscreen mode.
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
  
  // Pitch Timer (5-minute countdown)
  const pitchTimerEl = document.getElementById('pitchTimer');
  const timerTextEl = document.getElementById('timerText');
  let timerSeconds = 300; // 5 minutes countdown
  let timerInterval = null;
  let timerRunning = false;

  // Presenter Notes Database (Vietnamese)
  const presenterNotesData = [
    { slide: 1, title: "Slide 1: Mở đầu", time: "30s", notes: `<h4>Câu mở</h4><p>MentorMind biến video thao tác, lời giải thích và tài liệu sản xuất thành tri thức có kiểm chứng.</p><ul><li>Nhấn mạnh value proposition: video + lời chuyên gia → WorkProfile đã duyệt → AI Assistant có trích nguồn.</li><li>Định vị: giải pháp hỗ trợ con người, không thay thế chuyên gia.</li></ul>` },
    { slide: 2, title: "Slide 2: Vấn đề & insight", time: "45s", notes: `<h4>Câu chốt</h4><p><strong>Action khác Reason.</strong> Video cho thấy hành động; lý do phải được chuyên gia xác nhận.</p><ul><li>SOP thường không ghi đủ mẹo thực tế.</li><li>Không cho AI biến suy đoán thành know-how.</li></ul>` },
    { slide: 3, title: "Slide 3: Flow giải pháp", time: "50s", notes: `<h4>Ý chính</h4><ul><li>Input → Trích xuất → Hồ sơ nháp → Chuyên gia duyệt → Khai thác.</li><li>Transcript chỉ là artifact; output nghiệp vụ chính là WorkProfile có evidence.</li></ul>` },
    { slide: 4, title: "Slide 4: Kiến trúc & công nghệ", time: "55s", notes: `<h4>Ý chính</h4><ul><li>Trình bày trạng thái thật: đã implement, demo/đang nối, roadmap.</li><li>Nhấn mạnh data governance: public/synthetic, factory confidential, approved knowledge.</li></ul>` },
    { slide: 5, title: "Slide 5: Prototype validation", time: "45s", notes: `<h4>Ý chính</h4><ul><li>Team đã thử trên video LASI để chọn hướng VLM.</li><li>Thêm actor cải thiện recall/precision; 8B nhanh hơn 32B trong test này.</li><li>Nói rõ đây là preliminary, không overclaim accuracy sản xuất.</li></ul>` },
    { slide: 6, title: "Slide 6: Demo Golden Path", time: "55s", notes: `<h4>Ý chính</h4><ul><li>Demo một vertical slice PACK01: upload → review → hỏi assistant.</li><li>Nhấn câu guardrail: chưa có evidence đã duyệt thì hệ thống không được bịa.</li></ul>` },
    { slide: 7, title: "Slide 7: KPI & giá trị", time: "45s", notes: `<h4>Ý chính</h4><ul><li>Đánh giá bằng faithfulness, context precision/recall và thời gian tra cứu.</li><li>Business value: giữ tri thức, train người mới, hỗ trợ RCA, tôn trọng chuyên gia.</li></ul>` },
    { slide: 8, title: "Slide 8: Roadmap & kết luận", time: "35s", notes: `<h4>Câu kết</h4><p>Video cho biết chuyên gia làm gì. Chuyên gia cho biết tại sao. MentorMind biến cả hai thành tri thức có kiểm chứng.</p>` }
  ];

  // Initialize Slide Dots
  function initDots() {
    slideDotsContainer.innerHTML = '';
    slides.forEach((_, idx) => {
      const dot = document.createElement('button');
      dot.className = `slide-dot ${idx === 0 ? 'active' : ''}`;
      dot.title = `Đến slide ${idx + 1}`;
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
      const cat = catEl ? catEl.textContent.trim() : 'SECTION ' + (idx + 1);

      const thumb = document.createElement('div');
      thumb.className = `overview-thumb ${idx === currentSlideIndex ? 'active' : ''}`;
      thumb.innerHTML = `
        <span class="thumb-idx">${cat} · 0${idx + 1}</span>
        <h4 class="thumb-title">${title}</h4>
        <span class="thumb-desc">Bấm để chuyển slide</span>
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

  // Interactive Layer Inspector on Slide 7 (Vietnamese)
  const layersData = [
    { name: "Tầng 1: Thu thập đa phương thức", tag: "CAPTURE", desc: "Thu thập dữ liệu hiện trường mà không làm gián đoạn công việc:", details: ["Video thao tác theo công đoạn", "Audio giải thích của chuyên gia", "SOP, bản vẽ, Excel làm evidence bổ sung"] },
    { name: "Tầng 2: Chuẩn hóa tri thức", tag: "EXTRACT", desc: "Biến dữ liệu thô thành cấu trúc có thể duyệt:", details: ["Transcript segment và keyframe", "Step/action/observation theo timestamp", "WorkProfile draft với reason null nếu chưa có evidence"] },
    { name: "Tầng 3: Chuyên gia duyệt", tag: "HUMAN-IN-THE-LOOP", desc: "Không đưa tri thức vào KB nếu chưa được xác nhận:", details: ["Reviewer sửa key point, reason, ngoại lệ", "Gắn trạng thái draft/approved", "Giữ attribution và nguồn gốc tri thức"] },
    { name: "Tầng 4: Knowledge Base", tag: "VECTOR + GRAPH", desc: "Kết hợp truy vấn semantic và quan hệ nghiệp vụ:", details: ["PostgreSQL + pgvector cho search", "Neo4j cho quan hệ công đoạn-lỗi-nguyên nhân", "Mock Sigma để truy xuất lot/defect"] },
    { name: "Tầng 5: Agent & Evaluation", tag: "AGENT + EVAL", desc: "Kích hoạt tri thức sau duyệt:", details: ["Work Assistant trả lời có citation", "RCA Agent hỗ trợ 5-Why", "Ragas/Golden QA kiểm tra faithfulness và relevancy"] }
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
