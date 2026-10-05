/**
 * MentorMind — Denso Hackathon Interactive Presentation Controller (English Edition)
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

  // Presenter Notes Database (English)
  const presenterNotesData = [
    {
      slide: 1,
      title: "Slide 1: Introduction & Vision",
      time: "Target: 30s",
      notes: `
        <h4>Objective:</h4>
        <p>Establish high authority, project identity, and introduce the core mission for the Denso Hackathon judges.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Good morning esteemed Denso judges and committee members! We are team <strong>MentorMind</strong>.</li>
          <li>Our mission is: <em>Accumulate Master Know-How for AI to Learn</em>.</li>
          <li>Rather than requiring tedious, manual documentation that nobody reads, MentorMind captures tacit know-how directly from natural operational workflow and verbal reasoning.</li>
          <li>Today, we walk you through our 4 key pillars: Context, Problem Statement, Cautionary Lessons, and our 5-Layer System Architecture.</li>
        </ul>
      `
    },
    {
      slide: 2,
      title: "Slide 2: Context & Critical Pain Points",
      time: "Target: 45s",
      notes: `
        <h4>Objective:</h4>
        <p>Highlight the acute urgency of tacit knowledge loss in precision automotive manufacturing.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Why is this urgent for Denso? A massive retirement wave is cresting: veteran master technicians take decades of unwritten, instinctual know-how out the door.</li>
          <li>Traditional SOPs are static and cannot convey micro-gestures, hand orientation angles, or tactile feedback.</li>
          <li>In automotive precision assembly, a single millimeter misalignment in kitting triggers cascading defects across full batches.</li>
          <li>Multimodal VLM + GraphRAG provides the technical breakthrough needed to bridge this gap.</li>
        </ul>
      `
    },
    {
      slide: 3,
      title: "Slide 3: Challenge & 4 Deliverables",
      time: "Target: 45s",
      notes: `
        <h4>Objective:</h4>
        <p>Demonstrate exact alignment with the Denso Hackathon prompt and commit to 4 tangible deliverables.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>The Challenge: Capture workflows and reasoning into a centralized knowledge base, reusing tacit wisdom with LLMs — with zero manual documentation.</li>
          <li>Our 4 Core Deliverables over the 3-month roadmap:
            <ol>
              <li><strong>Standardized Template:</strong> WorkProfile JSON Schema capturing steps, reasons ("why"), and exceptions.</li>
              <li><strong>Hybrid Knowledge Base:</strong> Neo4j GraphRAG coupled with PostgreSQL pgvector.</li>
              <li><strong>Dual AI Assistants:</strong> Station-side apprentice assistant + 5-Why RCA Agent.</li>
              <li><strong>Usefulness Report:</strong> Rigorous Ragas benchmark scoring (Faithfulness &ge; 0.85).</li>
            </ol>
          </li>
        </ul>
      `
    },
    {
      slide: 4,
      title: "Slide 4: Case Study & Cautionary Ethics",
      time: "Target: 45s",
      notes: `
        <h4>Objective:</h4>
        <p>Set MentorMind apart by showcasing our ethical awareness and deep understanding of workplace psychology.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>We analyzed an investigative case study: <em>"Factory Workers Are Training AI to Replace Them… Here's the Truth"</em>.</li>
          <li>In that case, workers wore head-mounted cameras throughout full shifts to capture egocentric motor skills for cheap lab training.</li>
          <li>The consequence: Workers realized they were training their replacements — creating immediate distrust, passive sabotage, and knowledge hoarding.</li>
          <li>Critical insight: Any AI system that makes artisans feel covertly exploited will face instant rejection on the factory floor!</li>
        </ul>
      `
    },
    {
      slide: 5,
      title: "Slide 5: Paradigm Shift: Two Opposing Approaches",
      time: "Target: 45s",
      notes: `
        <h4>Objective:</h4>
        <p>Deliver the core philosophical punchline: "Capture & Empower" versus "Extract & Replace".</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>This comparison is the soul of MentorMind:
            <ul>
              <li><strong>Extract & Replace:</strong> Treats humans as temporary data farms to be automated away.</li>
              <li><strong>Capture & Empower (MentorMind):</strong> Treats master artisans as respected mentors whose names and insights are cited in every AI response.</li>
            </ul>
          </li>
          <li>Technicians earn tangible career benefits and bonus recognition when sharing the "why" behind their techniques.</li>
        </ul>
      `
    },
    {
      slide: 6,
      title: "Slide 6: The 4-Step MentorMind Loop",
      time: "Target: 45s",
      notes: `
        <h4>Objective:</h4>
        <p>Explain the elegant, frictionless operational loop from station camera to active assistant.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li><strong>Step 1 - Capture:</strong> Fixed station camera records 3–5 min normal work cycles without altering takt time.</li>
          <li><strong>Step 2 - Explain & Incentivize:</strong> Master takes 30s to explain "why rotate 90°?" and receives immediate bonus credit.</li>
          <li><strong>Step 3 - Multimodal AI Processing:</strong> 3-pass VLM (Qwen3-VL self-hosted) + Docling OCR auto-generates WorkProfile drafts. Master simply clicks "Approve".</li>
          <li><strong>Step 4 - Store & Activate:</strong> GraphRAG + Vector ingestion with permanent expert attribution.</li>
        </ul>
      `
    },
    {
      slide: 7,
      title: "Slide 7: 5-Layer Technical Architecture",
      time: "Target: 60s",
      notes: `
        <h4>Objective:</h4>
        <p>Convince technical judges of enterprise viability: self-hosted VLM, data security, GraphRAG, and dual agents.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Our 5-Layer Engineering Architecture:
            <ul>
              <li><strong>Layer 1: Multimodal Ingestion:</strong> 4–8 fps video, audio commentary, Docling OCR for blueprints & SOPs.</li>
              <li><strong>Layer 2: Multimodal VLM:</strong> Air-gapped self-hosted Qwen3-VL 8B (BF16 on 24GB GPU) with MediaPipe Hands temporal segmentation.</li>
              <li><strong>Layer 3: Knowledge Base:</strong> PostgreSQL pgvector (Dense HNSW + Lexical RRF) + Neo4j Graph + Sigma MES Adapter.</li>
              <li><strong>Layer 4: Dual Agents:</strong> Station Work Assistant (strict refusal guards & citations) + RCA 5-Why Agent.</li>
              <li><strong>Layer 5: Continuous Evaluation:</strong> Automated Ragas metrics (Faithfulness &ge; 0.85).</li>
            </ul>
          </li>
        </ul>
      `
    },
    {
      slide: 8,
      title: "Slide 8: 3-Month Roadmap & Vision",
      time: "Target: 30s",
      notes: `
        <h4>Objective:</h4>
        <p>Close with a crisp, credible timeline and an inspiring human-centric vision statement.</p>
        <h4>Key Talking Points:</h4>
        <ul>
          <li>Month 1: Standardization & Capture pipeline; Month 2: Knowledge Base & Dual Agents; Month 3: Ragas evaluation & Denso kitting pilot.</li>
          <li>We conclude with our founding motto: <em>"Preserve Master Know-How — Empower Human Artisans, Never Replace Them."</em></li>
          <li>Thank you, and we welcome your questions!</li>
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
      dot.title = `Go to Slide ${idx + 1}`;
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
        <span class="thumb-desc">Click to jump to slide</span>
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

  // Interactive Layer Inspector on Slide 7 (English)
  const layersData = [
    {
      name: "Layer 1: Capture & Multimodal Ingestion",
      tag: "MULTIMODAL INGESTION",
      desc: "Captures high-fidelity factory data without interrupting active production flows:",
      details: [
        "Station camera: 4–8 fps video sampling optimized for rapid hand movements",
        "Commentary mic: Captures spontaneous artisan verbal explanations",
        "Docling / mmore: Structured OCR extraction of engineering drawings and assembly SOPs"
      ]
    },
    {
      name: "Layer 2: Multimodal VLM Pipeline",
      tag: "3-PASS VLM PIPELINE",
      desc: "Transforms raw video and speech into structured WorkProfiles via a 3-pass loop:",
      details: [
        "Pass 1 - Segmentation: MediaPipe Hands detects gesture boundaries and action cadence",
        "Pass 2 - Action Description: Self-hosted Qwen3-VL 8B (BF16) outputs steps, key points, and reasons",
        "Pass 3 - Task Graph Synthesis: Resolves conflicting actions and enforces JSON schema compliance"
      ]
    },
    {
      name: "Layer 3: Hybrid Knowledge Base",
      tag: "GRAPHRAG & PGVECTOR",
      desc: "Combines explicit structural graph relationships with semantic vector retrieval:",
      details: [
        "Neo4j Knowledge Graph: Models Equipment –has→ Symptom –caused_by→ RootCause –fixed_by→ Procedure",
        "PostgreSQL + pgvector: Hybrid dense HNSW + lexical full-text search merged via Reciprocal Rank Fusion (RRF)",
        "Sigma MES Adapter: Binds WorkProfiles to real lot numbers, product IDs, and defect histories"
      ]
    },
    {
      name: "Layer 4: Dual AI Agents",
      tag: "SPECIALIZED AGENTS",
      desc: "Two purpose-built agents catering to distinct factory personas:",
      details: [
        "Work Assistant: Real-time station Q&A for novice technicians with strict source citations and refusal guards",
        "RCA Agent: 5-Why root cause analysis assistant for shift leads, cross-referencing past incidents and generating A3/8D drafts"
      ]
    },
    {
      name: "Layer 5: Continuous Evaluation",
      tag: "CONTINUOUS EVALUATION",
      desc: "Empirical benchmarking and shopfloor business KPI validation:",
      details: [
        "Ragas Benchmark: Guarantees Faithfulness ≥ 0.85 and Answer Relevancy ≥ 0.80 on curated golden QA sets",
        "Shopfloor A/B Testing: Quantifies defect resolution time reduction and first-time-right assembly rates"
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
