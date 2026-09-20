import React, { useState, useEffect } from 'react';
import './index.css';

const PRESETS = [
  {
    name: '💻 Dev Sprint',
    desc: 'Deep coding + standup + review',
    tasks: [
      { name: "Python Study & Architecture", duration_minutes: 120, priority: "high", fixed: false },
      { name: "Daily Team Standup", duration_minutes: 30, priority: "high", fixed: true, start_time: "10:00" },
      { name: "Code Review & PRs", duration_minutes: 45, priority: "medium", fixed: false },
      { name: "Bug Triaging", duration_minutes: 45, priority: "low", fixed: false }
    ],
    prompt: "Optimize my day for deep coding focus with buffer after the team standup."
  },
  {
    name: '🎓 Student Exam Prep',
    desc: 'Study blocks + revision',
    tasks: [
      { name: "Math Practice Test", duration_minutes: 90, priority: "high", fixed: false },
      { name: "Professor Consultation", duration_minutes: 45, priority: "high", fixed: true, start_time: "11:00" },
      { name: "Physics Problem Sets", duration_minutes: 75, priority: "high", fixed: false },
      { name: "Flashcards Revision", duration_minutes: 30, priority: "low", fixed: false }
    ],
    prompt: "Schedule high-focus study sessions before lunch and leave evening for light review."
  },
  {
    name: '⚖️ Balanced Day',
    desc: 'Deep work + workout + reading',
    tasks: [
      { name: "Deep Work Session", duration_minutes: 90, priority: "high", fixed: false },
      { name: "Client Strategy Call", duration_minutes: 45, priority: "high", fixed: true, start_time: "10:30" },
      { name: "Gym & Workout", duration_minutes: 60, priority: "medium", fixed: false },
      { name: "Reading & Research", duration_minutes: 45, priority: "low", fixed: false }
    ],
    prompt: "Make sure I have regular breaks and finish all deep work by late afternoon."
  }
];

function getTaskIcon(name) {
  const n = name.toLowerCase();
  if (n.includes('meeting') || n.includes('standup') || n.includes('sync') || n.includes('call') || n.includes('consultation')) return '👥';
  if (n.includes('study') || n.includes('exam') || n.includes('test') || n.includes('physics') || n.includes('math')) return '📚';
  if (n.includes('code') || n.includes('python') || n.includes('dev') || n.includes('bug') || n.includes('architecture')) return '💻';
  if (n.includes('gym') || n.includes('workout') || n.includes('run') || n.includes('walk')) return '💪';
  if (n.includes('read') || n.includes('research') || n.includes('write')) return '📖';
  if (n.includes('break') || n.includes('lunch') || n.includes('coffee')) return '☕';
  return '🎯';
}

function calculateDuration(start, end) {
  if (!start || !end) return 0;
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  return (eh * 60 + em) - (sh * 60 + sm);
}

function App() {
  const [tasks, setTasks] = useState(PRESETS[0].tasks);
  const [newTask, setNewTask] = useState({ name: "", duration_minutes: 60, priority: "medium", fixed: false, start_time: "09:00" });
  const [settings, setSettings] = useState({ date: "2026-09-20", start_time: "08:00", end_time: "20:00", break_minutes: 15 });
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("AI is analyzing your schedule...");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [toastMsg, setToastMsg] = useState(null);

  // Dynamic status messages during loading
  useEffect(() => {
    if (!isLoading) return;
    const messages = [
      "Analyzing available time windows...",
      "Resolving task priorities & constraints...",
      "Inserting intelligent energy recovery breaks...",
      "Verifying zero conflicts in schedule..."
    ];
    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % messages.length;
      setLoadingText(messages[idx]);
    }, 2000);
    return () => clearInterval(interval);
  }, [isLoading]);

  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleAddTask = (e) => {
    e.preventDefault();
    if (!newTask.name.trim()) return;
    
    const taskObj = {
      name: newTask.name.trim(),
      duration_minutes: parseInt(newTask.duration_minutes) || 30,
      priority: newTask.priority,
      fixed: newTask.fixed,
      start_time: newTask.fixed ? newTask.start_time : undefined
    };

    setTasks([...tasks, taskObj]);
    setNewTask({ name: "", duration_minutes: 60, priority: "medium", fixed: false, start_time: "09:00" });
  };

  const handleRemoveTask = (index) => {
    setTasks(tasks.filter((_, i) => i !== index));
  };

  const applyPreset = (preset) => {
    setTasks(preset.tasks);
    setPrompt(preset.prompt);
    showToast(`Loaded "${preset.name}" preset!`);
  };

  const handlePlanDay = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...settings,
          tasks,
          natural_language_request: prompt
        })
      });

      const data = await response.json();
      if (data.success) {
        setResult(data);
      } else {
        setError(data.error || "Could not generate plan.");
        setResult(data);
      }
    } catch (err) {
      setError("Failed to connect to backend server: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Find schedule data
  let scheduleData = null;
  let valData = null;
  if (result && result.observations) {
    const schedObs = result.observations.find(o => 
      (o.tool_name === 'create_schedule' || o.tool_name === 'tool_create_schedule') && o.success
    );
    if (schedObs && schedObs.data && schedObs.data.schedule) {
      scheduleData = schedObs.data.schedule;
    }

    const valObs = result.observations.find(o => 
      (o.tool_name === 'validate_schedule' || o.tool_name === 'tool_validate_schedule') && o.success
    );
    if (valObs && valObs.data) {
      valData = valObs.data;
    }
  }

  // Calculate stats
  let totalFocusMinutes = 0;
  let totalBreakMinutes = 0;
  let meetingMinutes = 0;

  if (scheduleData) {
    scheduleData.forEach(item => {
      const dur = calculateDuration(item.start, item.end);
      if (item.task === 'Break') {
        totalBreakMinutes += dur;
      } else if (item.task.toLowerCase().includes('meeting') || item.task.toLowerCase().includes('standup')) {
        meetingMinutes += dur;
      } else {
        totalFocusMinutes += dur;
      }
    });
  }

  const totalTrackedMinutes = totalFocusMinutes + totalBreakMinutes + meetingMinutes || 1;
  const focusPct = Math.round((totalFocusMinutes / totalTrackedMinutes) * 100);
  const meetingPct = Math.round((meetingMinutes / totalTrackedMinutes) * 100);
  const breakPct = Math.round((totalBreakMinutes / totalTrackedMinutes) * 100);

  const copySchedule = () => {
    if (!scheduleData) return;
    const text = scheduleData.map(s => `${s.start} - ${s.end} : ${s.task}`).join('\n');
    navigator.clipboard.writeText(`📅 Daily Schedule (${settings.date})\n\n` + text);
    showToast("Schedule copied to clipboard!");
  };

  return (
    <div className="app-wrapper">
      {/* Top Header */}
      <header className="top-nav">
        <div>
          <div className="brand-badge">
            <span className="brand-dot"></span>
            Chronos AI Agent
          </div>
          <h1 className="hero-title">Daily Planner</h1>
          <p className="hero-sub">Autonomous AI scheduling engine powered by FastMCP</p>
        </div>

        <div className="live-pill">
          <span className="live-pulse"></span>
          <span>Engine Online</span>
        </div>
      </header>

      {/* Preset Quick Fill Bar */}
      <div className="template-bar">
        <span style={{fontSize: '0.8rem', color: 'var(--text-muted)', alignSelf: 'center', marginRight: '0.25rem'}}>Quick Presets:</span>
        {PRESETS.map((preset, idx) => (
          <button 
            key={idx} 
            type="button" 
            className="template-pill"
            onClick={() => applyPreset(preset)}
          >
            {preset.name}
          </button>
        ))}
      </div>

      {/* Main Grid */}
      <div className="main-grid">
        
        {/* Left Column: Configuration & Tasks */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          
          {/* Day Settings */}
          <div className="glass-panel">
            <div className="panel-header">
              <h2 className="panel-title">
                <span className="panel-icon">⏱</span>
                Active Time Window
              </h2>
            </div>

            <div className="input-row" style={{marginBottom: '0.75rem'}}>
              <div>
                <label className="field-label">Start Hour</label>
                <input 
                  type="time" 
                  className="input-modern"
                  value={settings.start_time} 
                  onChange={(e) => setSettings({...settings, start_time: e.target.value})} 
                />
              </div>
              <div>
                <label className="field-label">End Hour</label>
                <input 
                  type="time" 
                  className="input-modern"
                  value={settings.end_time} 
                  onChange={(e) => setSettings({...settings, end_time: e.target.value})} 
                />
              </div>
            </div>

            <div className="input-row">
              <div>
                <label className="field-label">Date</label>
                <input 
                  type="date" 
                  className="input-modern"
                  value={settings.date} 
                  onChange={(e) => setSettings({...settings, date: e.target.value})} 
                />
              </div>
              <div>
                <label className="field-label">Buffer Break (min)</label>
                <input 
                  type="number" 
                  className="input-modern"
                  value={settings.break_minutes} 
                  onChange={(e) => setSettings({...settings, break_minutes: parseInt(e.target.value) || 15})} 
                />
              </div>
            </div>
          </div>

          {/* Tasks Creator */}
          <div className="glass-panel">
            <div className="panel-header">
              <h2 className="panel-title">
                <span className="panel-icon">📝</span>
                Tasks & Events
              </h2>
              <span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>{tasks.length} items</span>
            </div>

            <form onSubmit={handleAddTask}>
              <div style={{marginBottom: '0.75rem'}}>
                <label className="field-label">Task Name</label>
                <input 
                  type="text" 
                  className="input-modern"
                  placeholder="e.g., Deep Python Study, Team Sync..." 
                  value={newTask.name} 
                  onChange={(e) => setNewTask({...newTask, name: e.target.value})} 
                  required 
                />
              </div>

              <div className="input-row" style={{marginBottom: '0.75rem'}}>
                <div>
                  <label className="field-label">Duration (Minutes)</label>
                  <input 
                    type="number" 
                    className="input-modern"
                    min="10"
                    step="5"
                    value={newTask.duration_minutes} 
                    onChange={(e) => setNewTask({...newTask, duration_minutes: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">Priority</label>
                  <select 
                    className="select-modern"
                    value={newTask.priority} 
                    onChange={(e) => setNewTask({...newTask, priority: e.target.value})}
                  >
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Low Priority</option>
                  </select>
                </div>
              </div>

              <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem'}}>
                <input 
                  type="checkbox" 
                  id="fixedCheckbox" 
                  style={{width: 'auto', margin: 0}}
                  checked={newTask.fixed} 
                  onChange={(e) => setNewTask({...newTask, fixed: e.target.checked})} 
                />
                <label htmlFor="fixedCheckbox" style={{fontSize: '0.825rem', color: 'var(--text-dim)', cursor: 'pointer'}}>
                  Fixed event (starts at exact time)
                </label>
              </div>

              {newTask.fixed && (
                <div style={{marginBottom: '0.75rem'}}>
                  <label className="field-label">Fixed Start Time</label>
                  <input 
                    type="time" 
                    className="input-modern"
                    value={newTask.start_time} 
                    onChange={(e) => setNewTask({...newTask, start_time: e.target.value})} 
                    required 
                  />
                </div>
              )}

              <button type="submit" className="btn-secondary" style={{width: '100%'}}>
                + Add to Agenda
              </button>
            </form>

            {/* Tasks list */}
            <div className="task-items-container">
              {tasks.map((task, idx) => (
                <div key={idx} className="task-card-mini">
                  <div className="task-left">
                    <span className="task-category-icon">{getTaskIcon(task.name)}</span>
                    <div>
                      <div className="task-title-text">{task.name}</div>
                      <div className="task-meta-text">
                        {task.duration_minutes} mins {task.fixed ? `• Fixed at ${task.start_time}` : ''}
                      </div>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                    <span className={`pill-priority ${task.fixed ? 'priority-fixed' : `priority-${task.priority}`}`}>
                      {task.fixed ? 'Fixed' : task.priority}
                    </span>
                    <button 
                      className="btn-icon-del" 
                      title="Remove Task" 
                      onClick={() => handleRemoveTask(idx)}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: AI Generation & Timeline */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          
          {/* Prompt / Instructions */}
          <div className="glass-panel">
            <div className="panel-header">
              <h2 className="panel-title">
                <span className="panel-icon">✨</span>
                AI Scheduling Strategy
              </h2>
            </div>

            <textarea 
              rows="2" 
              className="textarea-modern"
              style={{resize: 'none', marginBottom: '1rem'}}
              placeholder="Give personalized instructions to the agent..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />

            <button 
              className="btn-primary" 
              onClick={handlePlanDay} 
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span style={{display: 'inline-block', animation: 'spin 1s linear infinite'}}>⚡</span>
                  Generating Perfect Day...
                </>
              ) : (
                <>
                  <span>⚡</span>
                  Plan My Day
                </>
              )}
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="glass-panel" style={{borderColor: 'rgba(244, 63, 94, 0.4)', background: 'rgba(244, 63, 94, 0.08)'}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fb7185', fontWeight: 600}}>
                <span>⚠️</span>
                <span>Error generating plan</span>
              </div>
              <p style={{margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: '#fecdd3'}}>{error}</p>
            </div>
          )}

          {/* Loading Radar Animation */}
          {isLoading && (
            <div className="glass-panel planning-loader">
              <div className="pulse-rings">
                <div className="ring"></div>
                <div className="ring"></div>
                <div className="ring"></div>
                <div className="ring-center-icon">⚡</div>
              </div>
              <div className="loader-title">Synthesizing Schedule</div>
              <div className="loader-sub">{loadingText}</div>
            </div>
          )}

          {/* AI Plan Summary */}
          {result && result.answer && !isLoading && (
            <div className="ai-summary-box">
              <div className="ai-sparkle-header">
                <span className="ai-tag">
                  <span>✨</span>
                  AI Strategic Briefing
                </span>
                {valData && valData.valid && (
                  <span style={{fontSize: '0.75rem', background: 'rgba(16, 185, 129, 0.2)', color: '#6ee7b7', padding: '0.2rem 0.6rem', borderRadius: '999px', fontWeight: 600}}>
                    ✓ Verified Conflict-Free
                  </span>
                )}
              </div>
              <p className="ai-summary-text">{result.answer}</p>
            </div>
          )}

          {/* Day Analytics & Visual Timeline */}
          {scheduleData && !isLoading && (
            <div className="glass-panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">
                    <span className="panel-icon">📅</span>
                    Master Timeline
                  </h2>
                  <span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>{settings.date} • {scheduleData.length} scheduled intervals</span>
                </div>

                <div style={{display: 'flex', gap: '0.5rem'}}>
                  <button className="btn-secondary" onClick={copySchedule}>
                    📋 Copy Schedule
                  </button>
                </div>
              </div>

              {/* Stats Bar */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-val">{Math.round((totalFocusMinutes / 60) * 10) / 10}h</div>
                  <div className="stat-lbl">Deep Work</div>
                </div>
                <div className="stat-card">
                  <div className="stat-val">{totalBreakMinutes}m</div>
                  <div className="stat-lbl">Rest & Buffer</div>
                </div>
                <div className="stat-card">
                  <div className="stat-val">{scheduleData.filter(s => s.task !== 'Break').length}</div>
                  <div className="stat-lbl">Tasks Done</div>
                </div>
              </div>

              {/* Visual Breakdown Bar */}
              <div className="time-dist-container">
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)'}}>
                  <span>Energy & Time Distribution</span>
                  <span>{Math.round(totalTrackedMinutes / 60 * 10) / 10} Total Hours Scheduled</span>
                </div>
                <div className="dist-bar-wrapper">
                  <div className="dist-segment focus" style={{width: `${focusPct}%`}} title={`Focus Work: ${focusPct}%`}></div>
                  <div className="dist-segment meeting" style={{width: `${meetingPct}%`}} title={`Meetings: ${meetingPct}%`}></div>
                  <div className="dist-segment break" style={{width: `${breakPct}%`}} title={`Breaks: ${breakPct}%`}></div>
                </div>
                <div className="dist-legend">
                  <div className="legend-item"><span className="legend-dot" style={{background: '#6366f1'}}></span> Focus ({focusPct}%)</div>
                  <div className="legend-item"><span className="legend-dot" style={{background: '#06b6d4'}}></span> Meetings ({meetingPct}%)</div>
                  <div className="legend-item"><span className="legend-dot" style={{background: '#10b981'}}></span> Breaks ({breakPct}%)</div>
                </div>
              </div>

              {/* Timeline Cards */}
              <div className="timeline-modern">
                {scheduleData.map((item, idx) => {
                  const isBreak = item.task === 'Break';
                  const isMeeting = item.task.toLowerCase().includes('meeting') || item.task.toLowerCase().includes('standup');
                  const duration = calculateDuration(item.start, item.end);

                  return (
                    <div 
                      key={idx} 
                      className={`timeline-slot-card ${isBreak ? 'is-break' : isMeeting ? 'is-meeting' : ''}`}
                    >
                      <div className="slot-left">
                        <div className="slot-time-badge">
                          <span style={{color: isBreak ? '#34d399' : '#818cf8'}}>●</span>
                          {item.start} - {item.end}
                        </div>
                        <div className="slot-task-title">
                          <span>{getTaskIcon(item.task)}</span>
                          <span style={{color: isBreak ? '#a7f3d0' : 'inherit'}}>{item.task}</span>
                        </div>
                      </div>

                      <div className="slot-duration-pill">
                        {duration} mins
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Empty state before planning */}
          {!scheduleData && !isLoading && (
            <div className="glass-panel empty-timeline">
              <div className="empty-icon">🪐</div>
              <h3 style={{color: 'var(--text-dim)', marginBottom: '0.4rem'}}>No Schedule Generated Yet</h3>
              <p style={{margin: 0, fontSize: '0.875rem'}}>Configure your tasks on the left and click <strong>"Plan My Day"</strong> to let the AI build your ideal itinerary.</p>
            </div>
          )}

        </div>

      </div>

      {/* Floating Toast Notification */}
      {toastMsg && (
        <div className="toast-notice">
          {toastMsg}
        </div>
      )}
    </div>
  );
}

export default App;
