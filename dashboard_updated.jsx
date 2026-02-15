import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { createClient } from '@supabase/supabase-js';

// Supabase configuration - Replace with your actual values
const supabase = createClient(
  'https://nlijrpfuzcxftbcuwzte.supabase.co',  // e.g., 'https://xxxxx.supabase.co'
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5saWpycGZ1emN4ZnRiY3V3enRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA5MjcwODQsImV4cCI6MjA4NjUwMzA4NH0.SbZFfPwBLPSBK0DkWs00IGFtrnPHtvKXQefg43fL6Dg'  // Your anon/public key
);

// Utility to generate sample data
const generateSampleData = () => ({
  finance: [
    // January
    { date: '2/1', fullDate: '2026-01-02', amount: 134, category: 'groceries' },
    { date: '5/1', fullDate: '2026-01-05', amount: 89, category: 'dining' },
    { date: '8/1', fullDate: '2026-01-08', amount: 45, category: 'transport' },
    { date: '10/1', fullDate: '2026-01-10', amount: 156, category: 'groceries' },
    { date: '12/1', fullDate: '2026-01-12', amount: 78, category: 'dining' },
    { date: '15/1', fullDate: '2026-01-15', amount: 234, category: 'groceries' },
    { date: '18/1', fullDate: '2026-01-18', amount: 92, category: 'entertainment' },
    { date: '20/1', fullDate: '2026-01-20', amount: 67, category: 'dining' },
    { date: '23/1', fullDate: '2026-01-23', amount: 145, category: 'groceries' },
    { date: '25/1', fullDate: '2026-01-25', amount: 54, category: 'transport' },
    { date: '28/1', fullDate: '2026-01-28', amount: 89, category: 'dining' },
    { date: '30/1', fullDate: '2026-01-30', amount: 178, category: 'groceries' },
    
    // February (current)
    { date: '2/2', fullDate: '2026-02-02', amount: 198, category: 'groceries' },
    { date: '4/2', fullDate: '2026-02-04', amount: 76, category: 'dining' },
    { date: '7/2', fullDate: '2026-02-07', amount: 145, category: 'groceries' },
    { date: '8/2', fullDate: '2026-02-08', amount: 52, category: 'dining' },
    { date: '9/2', fullDate: '2026-02-09', amount: 89, category: 'transport' },
    { date: '10/2', fullDate: '2026-02-10', amount: 220, category: 'groceries' },
    { date: '11/2', fullDate: '2026-02-11', amount: 75, category: 'dining' },
    { date: '12/2', fullDate: '2026-02-12', amount: 45, category: 'entertainment' },
    { date: '13/2', fullDate: '2026-02-13', amount: 67, category: 'dining' },
    
    // December (for 3-month view)
    { date: '5/12', fullDate: '2025-12-05', amount: 156, category: 'groceries' },
    { date: '8/12', fullDate: '2025-12-08', amount: 92, category: 'dining' },
    { date: '12/12', fullDate: '2025-12-12', amount: 234, category: 'groceries' },
    { date: '15/12', fullDate: '2025-12-15', amount: 67, category: 'transport' },
    { date: '18/12', fullDate: '2025-12-18', amount: 145, category: 'entertainment' },
    { date: '20/12', fullDate: '2025-12-20', amount: 89, category: 'dining' },
    { date: '23/12', fullDate: '2025-12-23', amount: 178, category: 'groceries' },
    { date: '27/12', fullDate: '2025-12-27', amount: 234, category: 'dining' },
    { date: '30/12', fullDate: '2025-12-30', amount: 123, category: 'groceries' }
  ],
  dating: {
    activePursuit: [
      { name: 'Sarah', notes: 'Met 14/2, went well. Coffee date planned for Sat' },
      { name: 'Jessica', notes: 'Dinner 10/2, good chemistry. Text her Thursday' },
      { name: 'Olivia', notes: 'Met 8/2 drinks, fun vibe. Following up this week' }
    ],
    onlineOnly: [
      { name: 'Emma', notes: 'Hinge match, chatting about travel. Ask her out soon' },
      { name: 'Sophie', notes: 'Bumble, architect, seems interesting' },
      { name: 'Mia', notes: 'Matched 12/2, good banter, getting her number' }
    ],
    backBurner: [
      { name: 'Rachel', notes: 'Went on 2 dates, lukewarm. Keep warm' },
      { name: 'Kate', notes: 'Met at party, got number, low priority' }
    ]
  },
  todos: [
    { id: 'sample-1', task: 'Q1 performance review', due: '2/18', priority: 'high', status: 'pending' },
    { id: 'sample-2', task: 'Dentist appointment', due: '2/21', priority: 'medium', status: 'pending' },
    { id: 'sample-3', task: 'File taxes', due: '3/15', priority: 'high', status: 'pending' }
  ],
  netWorth: Object.assign([
    { month: 'Sep', savings: 22000, trading: 8500, total: 30500 },
    { month: 'Oct', savings: 23500, trading: 9200, total: 32700 },
    { month: 'Nov', savings: 24000, trading: 8800, total: 32800 },
    { month: 'Dec', savings: 25500, trading: 10100, total: 35600 },
    { month: 'Jan', savings: 26000, trading: 11500, total: 37500 },
    { month: 'Feb', savings: 27000, trading: 12000, total: 39000 }
  ], { lastUpdated: '10/02/26' }),
  habits: { apps: 5, vlogs: 4, pm: 3 }
});

const App = () => {
  const [data, setData] = useState(generateSampleData());
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('week'); // 'week', 'month', 'quarter', 'all'

  useEffect(() => {
    loadData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    try {
      // Fetch data from Supabase
      const { data: entries, error } = await supabase
        .from('dashboard_entries')
        .select('*')
        .order('created_at', { ascending: false });
      
      if (error) {
        console.error('Supabase error:', error);
        // Fall back to sample data if error
        setLoading(false);
        return;
      }

      if (entries && entries.length > 0) {
        // Transform database entries into dashboard format
        const transformedData = transformEntries(entries);
        setData(transformedData);
      }
    } catch (err) {
      console.log('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Transform database entries into the format the dashboard expects
  const transformEntries = (entries) => {
    const finance = [];
    const dating = { activePursuit: [], onlineOnly: [], backBurner: [] };
    const todos = [];
    const netWorthRaw = [];
    const habits = { apps: 0, vlogs: 0, pm: 0 };

    // Current year for filtering habits
    const currentYear = new Date().getFullYear();

    entries.forEach(entry => {
      // Parse data if it's a string (bot saves as JSON string)
      const data = typeof entry.data === 'string' ? JSON.parse(entry.data) : entry.data;
      
      if (entry.category === 'finance') {
        const date = new Date(data.date || entry.created_at);
        finance.push({
          date: `${date.getDate()}/${date.getMonth() + 1}`,
          fullDate: data.date || entry.created_at,
          amount: Math.abs(data.amount || 0), // Use absolute value for display
          category: data.subcategory || data.description || 'other'
        });
      } else if (entry.category === 'net_worth') {
        netWorthRaw.push({
          date: data.date || entry.created_at.slice(0, 10),
          savings: data.savings,
          trading: data.trading,
          created_at: entry.created_at
        });
      } else if (entry.category === 'dating') {
        const person = {
          name: data.person || 'Unknown',
          notes: data.notes || data.activity || ''
        };
        
        // Map to dashboard categories based on new status field
        const status = data.status || 'backburner';
        if (status === 'active') {
          dating.activePursuit.push(person);
        } else if (status === 'texting') {
          dating.onlineOnly.push(person);
        } else {
          dating.backBurner.push(person);
        }
      } else if (entry.category === 'todos') {
        // Only show pending/in_progress todos
        if (data.status !== 'done') {
          todos.push({
            id: entry.id,               // Supabase row ID for updates
            entryData: data,             // Keep full data for PATCH
            task: data.task || 'Task',
            due: data.due || 'TBD',
            priority: data.priority || 'medium',
            status: data.status || 'pending',
            reminderTime: data.reminder_time || null
          });
        }
      } else if (entry.category === 'habits') {
        // Only count habits from current year
        const entryDate = new Date(data.date || entry.created_at);
        if (entryDate.getFullYear() === currentYear) {
          const habit = data.habit;
          if (habit in habits) {
            habits[habit] += 1;
          }
        }
      }
    });

    // Build net worth timeline: for each month, take the latest snapshot
    // and carry forward the last known value for each account
    const netWorth = buildNetWorthTimeline(netWorthRaw);

    return { finance, dating, todos, netWorth, habits };
  };

  // Build a 6-month net worth timeline from snapshots
  const buildNetWorthTimeline = (rawEntries) => {
    if (rawEntries.length === 0) return [];

    // Sort by date ascending
    const sorted = [...rawEntries].sort((a, b) => new Date(a.date) - new Date(b.date));

    // Track latest known values for each account
    let latestSavings = 0;
    let latestTrading = 0;

    // Group by month, keeping the latest entry per month
    const monthMap = {};
    let lastDate = '';
    sorted.forEach(entry => {
      if (entry.savings != null) latestSavings = entry.savings;
      if (entry.trading != null) latestTrading = entry.trading;
      lastDate = entry.date;

      const d = new Date(entry.date);
      const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;

      monthMap[monthKey] = {
        savings: latestSavings,
        trading: latestTrading,
        total: latestSavings + latestTrading
      };
    });

    // Get last 6 months
    const months = Object.keys(monthMap).sort().slice(-6);
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    // Format lastDate as DD/MM/YY
    const ld = new Date(lastDate);
    const lastUpdated = lastDate ? `${String(ld.getDate()).padStart(2,'0')}/${String(ld.getMonth()+1).padStart(2,'0')}/${String(ld.getFullYear()).slice(-2)}` : '';

    const timeline = months.map(key => {
      const [, m] = key.split('-');
      return {
        month: monthNames[parseInt(m) - 1],
        ...monthMap[key]
      };
    });

    // Attach lastUpdated to the array for display
    timeline.lastUpdated = lastUpdated;
    return timeline;
  };

  // Mark a todo as done — optimistic UI + Supabase update
  const markTodoDone = async (todoId, entryData) => {
    // Optimistic: remove from UI immediately
    setData(prev => ({
      ...prev,
      todos: prev.todos.filter(t => t.id !== todoId)
    }));

    // If it's a sample todo (no real Supabase ID), just remove from UI
    if (!todoId || String(todoId).startsWith('sample-')) return;

    const { error } = await supabase
      .from('dashboard_entries')
      .update({ data: { ...entryData, status: 'done' } })
      .eq('id', todoId);

    if (error) {
      console.error('Failed to mark todo done:', error);
      // Re-fetch to restore if failed
      loadData();
    }
  };

  // Filter finance data by time range
  const getFilteredFinanceData = () => {
    const now = new Date('2026-02-13'); // Current date
    let cutoffDate;
    
    switch(timeRange) {
      case 'week':
        cutoffDate = new Date(now);
        cutoffDate.setDate(cutoffDate.getDate() - 7);
        break;
      case 'month':
        cutoffDate = new Date(now);
        cutoffDate.setMonth(cutoffDate.getMonth() - 1);
        break;
      case 'quarter':
        cutoffDate = new Date(now);
        cutoffDate.setMonth(cutoffDate.getMonth() - 3);
        break;
      case 'all':
        return data.finance;
      default:
        cutoffDate = new Date(now);
        cutoffDate.setDate(cutoffDate.getDate() - 7);
    }
    
    return data.finance.filter(item => {
      const itemDate = new Date(item.fullDate);
      return itemDate >= cutoffDate;
    });
  };

  const filteredFinance = getFilteredFinanceData();

  // Consolidate spending per day for the bar chart
  const consolidatedFinance = Object.values(
    filteredFinance.reduce((acc, item) => {
      const key = item.fullDate;
      if (!acc[key]) {
        acc[key] = { date: item.date, fullDate: item.fullDate, amount: 0 };
      }
      acc[key].amount += item.amount;
      return acc;
    }, {})
  ).sort((a, b) => new Date(a.fullDate) - new Date(b.fullDate));

  // Calculate metrics
  const totalSpending = filteredFinance.reduce((sum, item) => sum + item.amount, 0);
  const totalDating = (data.dating?.activePursuit?.length || 0) + 
                      (data.dating?.onlineOnly?.length || 0) + 
                      (data.dating?.backBurner?.length || 0);

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        background: 'linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%)',
        color: '#00ff88',
        fontFamily: 'Courier New, monospace',
        fontSize: '18px'
      }}>
        Loading dashboard...
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%)',
      padding: '40px 20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
        
        @keyframes slideInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        
        .widget {
          animation: slideInUp 0.6s ease-out backwards;
        }
        
        .widget:nth-child(1) { animation-delay: 0.1s; }
        .widget:nth-child(2) { animation-delay: 0.2s; }
        .widget:nth-child(3) { animation-delay: 0.3s; }
        .widget:nth-child(4) { animation-delay: 0.4s; }
        .widget:nth-child(5) { animation-delay: 0.5s; }
        .widget:nth-child(6) { animation-delay: 0.6s; }
        
        .stat-number {
          font-family: 'Space Mono', monospace;
          font-size: 48px;
          font-weight: 700;
          line-height: 1;
          background: linear-gradient(135deg, #00ff88 0%, #00ffff 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        
        .live-indicator {
          animation: pulse 2s ease-in-out infinite;
          background: #00ff88;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          display: inline-block;
          margin-right: 8px;
          box-shadow: 0 0 12px #00ff88;
        }

        .todo-checkbox {
          width: 20px;
          height: 20px;
          border: 2px solid #444;
          border-radius: 6px;
          flex-shrink: 0;
          background: transparent;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #000;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .todo-checkbox:hover {
          border-color: #88ff00;
          background: #88ff0022;
        }
      `}</style>

      {/* Header */}
      <div style={{ maxWidth: '1100px', margin: '0 auto 60px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
          <span className="live-indicator"></span>
          <span style={{ 
            color: '#00ff88', 
            fontFamily: 'Space Mono, monospace',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '2px'
          }}>
            LIVE DASHBOARD
          </span>
        </div>
        <h1 style={{ 
          fontFamily: 'Syne, sans-serif',
          fontSize: '32px',
          fontWeight: '800',
          color: '#ffffff',
          margin: '0 0 8px 0',
          letterSpacing: '-1px',
          lineHeight: '1.2'
        }}>
          Dashbored v1.0
        </h1>
        <p style={{ 
          color: '#666',
          fontFamily: 'Space Mono, monospace',
          fontSize: '14px',
          margin: 0
        }}>
          Last synced: {new Date().toLocaleTimeString()} via Telegram Bot
        </p>
      </div>

      {/* Widgets Grid */}
      <div style={{ 
        maxWidth: '1100px', 
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '20px'
      }}>
        
        {/* Net Worth Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '24px',
          position: 'relative',
          overflow: 'hidden',
          gridColumn: 'span 2'
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: '300px',
            height: '300px',
            background: 'radial-gradient(circle, rgba(0,255,136,0.08) 0%, transparent 70%)',
            pointerEvents: 'none'
          }}></div>
          
          <div style={{ marginBottom: '24px' }}>
            <div style={{ 
              color: '#00ff88',
              fontSize: '12px',
              fontFamily: 'Space Mono, monospace',
              textTransform: 'uppercase',
              letterSpacing: '2px',
              marginBottom: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              🏦 Net Worth
              <span style={{ color: '#555', fontSize: '11px', textTransform: 'none', letterSpacing: '0' }}>
                {data.netWorth?.lastUpdated ? `updated ${data.netWorth.lastUpdated}` : ''}
              </span>
            </div>
            <div className="stat-number" style={{ fontSize: '56px' }}>
              ${(() => {
                const nw = data.netWorth;
                if (!nw || nw.length === 0) return '0';
                const latest = nw[nw.length - 1];
                return (latest.total || 0).toLocaleString();
              })()}
            </div>
            <div style={{ display: 'flex', gap: '24px', marginTop: '12px' }}>
              <div>
                <span style={{ color: '#666', fontSize: '12px', fontFamily: 'Space Mono, monospace', marginRight: '8px' }}>Savings</span>
                <span style={{ color: '#00ff88', fontSize: '16px', fontFamily: 'Space Mono, monospace', fontWeight: '700' }}>
                  ${(() => {
                    const nw = data.netWorth;
                    if (!nw || nw.length === 0) return '0';
                    return (nw[nw.length - 1].savings || 0).toLocaleString();
                  })()}
                </span>
              </div>
              <div>
                <span style={{ color: '#666', fontSize: '12px', fontFamily: 'Space Mono, monospace', marginRight: '8px' }}>Trading</span>
                <span style={{ color: '#00ffff', fontSize: '16px', fontFamily: 'Space Mono, monospace', fontWeight: '700' }}>
                  ${(() => {
                    const nw = data.netWorth;
                    if (!nw || nw.length === 0) return '0';
                    return (nw[nw.length - 1].trading || 0).toLocaleString();
                  })()}
                </span>
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={data.netWorth || []}>
              <XAxis dataKey="month" stroke="#444" style={{ fontSize: '11px' }} />
              <YAxis stroke="#444" style={{ fontSize: '11px' }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
              <Tooltip 
                contentStyle={{ background: '#0f0f0f', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
                formatter={(value) => [`$${value.toLocaleString()}`, '']}
              />
              <Line type="monotone" dataKey="total" stroke="#00ff88" strokeWidth={2} dot={{ fill: '#00ff88', r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Finance Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '24px',
          position: 'relative',
          overflow: 'hidden',
          gridColumn: 'span 2'
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: '200px',
            height: '200px',
            background: 'radial-gradient(circle, rgba(0,255,136,0.1) 0%, transparent 70%)',
            pointerEvents: 'none'
          }}></div>
          
          <div style={{ marginBottom: '24px' }}>
            <div style={{ 
              color: '#00ff88',
              fontSize: '12px',
              fontFamily: 'Space Mono, monospace',
              textTransform: 'uppercase',
              letterSpacing: '2px',
              marginBottom: '12px'
            }}>
              💰 Spending
            </div>
            <div className="stat-number">${totalSpending}</div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '4px' }}>
              {timeRange === 'week' && 'spent this week'}
              {timeRange === 'month' && 'spent this month'}
              {timeRange === 'quarter' && 'spent last 3 months'}
              {timeRange === 'all' && 'total spending'}
            </div>
          </div>

          {/* Time Range Selector */}
          <div style={{
            display: 'flex',
            gap: '8px',
            marginBottom: '20px',
            flexWrap: 'wrap'
          }}>
            {['week', 'month', 'quarter', 'all'].map(range => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                style={{
                  background: timeRange === range ? '#00ff8822' : '#1a1a1a',
                  border: timeRange === range ? '1px solid #00ff88' : '1px solid #333',
                  color: timeRange === range ? '#00ff88' : '#666',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  fontFamily: 'Space Mono, monospace',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {range === 'quarter' ? '3 months' : range}
              </button>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={consolidatedFinance.slice(-20)}>
              <Bar dataKey="amount" fill="#00ff88" radius={[4, 4, 0, 0]} />
              <XAxis dataKey="date" stroke="#444" style={{ fontSize: '11px' }} />
              <YAxis stroke="#444" style={{ fontSize: '11px' }} />
              <Tooltip 
                contentStyle={{ 
                  background: '#0f0f0f', 
                  border: '1px solid #333',
                  borderRadius: '8px',
                  fontSize: '12px'
                }}
              />
            </BarChart>
          </ResponsiveContainer>

          <div style={{ marginTop: '20px' }}>
            {filteredFinance.slice(-3).map((item, i) => (
              <div key={i} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 0',
                borderBottom: i < 2 ? '1px solid #222' : 'none',
                fontSize: '13px'
              }}>
                <span style={{ color: '#999' }}>{item.date} • {item.category}</span>
                <span style={{ color: '#fff', fontFamily: 'Space Mono, monospace' }}>
                  ${item.amount}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Todos Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '24px',
          gridColumn: 'span 2'
        }}>
          <div style={{ 
            color: '#88ff00',
            fontSize: '12px',
            fontFamily: 'Space Mono, monospace',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            marginBottom: '20px'
          }}>
            ✅ To-Do ({data.todos.length})
          </div>

          {data.todos.length === 0 && (
            <div style={{ color: '#666', fontSize: '13px', fontStyle: 'italic' }}>
              All done! 🎉
            </div>
          )}

          {data.todos.map((todo, i) => (
            <div key={todo.id || i} style={{
              background: '#1a1a1a',
              border: todo.priority === 'high' ? '1px solid #88ff0044' : '1px solid #2a2a2a',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <div
                className="todo-checkbox"
                onClick={() => markTodoDone(todo.id, todo.entryData)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && markTodoDone(todo.id, todo.entryData)}
              />
              <div style={{ flex: 1 }}>
                <div style={{ 
                  color: '#fff',
                  fontSize: '14px',
                  marginBottom: '4px'
                }}>
                  {todo.task}
                </div>
                <div style={{ 
                  color: '#666',
                  fontSize: '12px',
                  fontFamily: 'Space Mono, monospace'
                }}>
                  Due: {todo.due} • {todo.priority}
                  {todo.reminderTime && (() => {
                    try {
                      const rt = new Date(todo.reminderTime);
                      const dd = String(rt.getDate()).padStart(2, '0');
                      const mm = String(rt.getMonth() + 1).padStart(2, '0');
                      const time = rt.toLocaleTimeString('en-SG', { hour: 'numeric', minute: '2-digit', hour12: true });
                      return <span style={{ color: '#ffaa00' }}> • 🔔 {dd}/{mm} {time}</span>;
                    } catch { return null; }
                  })()}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Dating Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '24px',
          gridColumn: 'span 2'
        }}>
          <div style={{ marginBottom: '24px' }}>
            <div style={{ 
              color: '#ff0088',
              fontSize: '12px',
              fontFamily: 'Space Mono, monospace',
              textTransform: 'uppercase',
              letterSpacing: '2px',
              marginBottom: '12px'
            }}>
              💕 Dating Funnel
            </div>
            <div className="stat-number" style={{
              background: 'linear-gradient(135deg, #ff0088 0%, #ff8800 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              {totalDating}
            </div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '4px' }}>
              total in pipeline
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '20px'
          }}>
            {/* Active Pursuit List */}
            <div>
              <div style={{
                color: '#ff0088',
                fontSize: '13px',
                fontWeight: '600',
                marginBottom: '16px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                fontFamily: 'Space Mono, monospace'
              }}>
                Active Pursuit ({data.dating.activePursuit.length})
              </div>
              {data.dating.activePursuit.map((person, i) => (
                <div key={i} style={{
                  background: '#1a1a1a',
                  border: '1px solid #ff008844',
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '12px'
                }}>
                  <div style={{ 
                    color: '#fff',
                    fontWeight: '600',
                    fontSize: '15px',
                    marginBottom: '8px'
                  }}>
                    {person.name}
                  </div>
                  <div style={{ 
                    color: '#999',
                    fontSize: '12px',
                    lineHeight: '1.5'
                  }}>
                    {person.notes}
                  </div>
                </div>
              ))}
            </div>

            {/* Online Only List */}
            <div>
              <div style={{
                color: '#ffaa00',
                fontSize: '13px',
                fontWeight: '600',
                marginBottom: '16px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                fontFamily: 'Space Mono, monospace'
              }}>
                Online Only ({data.dating.onlineOnly.length})
              </div>
              {data.dating.onlineOnly.map((person, i) => (
                <div key={i} style={{
                  background: '#1a1a1a',
                  border: '1px solid #ffaa0033',
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '12px'
                }}>
                  <div style={{ 
                    color: '#fff',
                    fontWeight: '600',
                    fontSize: '15px',
                    marginBottom: '8px'
                  }}>
                    {person.name}
                  </div>
                  <div style={{ 
                    color: '#999',
                    fontSize: '12px',
                    lineHeight: '1.5'
                  }}>
                    {person.notes}
                  </div>
                </div>
              ))}
            </div>

            {/* Back Burner List */}
            <div>
              <div style={{
                color: '#666',
                fontSize: '13px',
                fontWeight: '600',
                marginBottom: '16px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                fontFamily: 'Space Mono, monospace'
              }}>
                Back Burner ({data.dating.backBurner.length})
              </div>
              {data.dating.backBurner.map((person, i) => (
                <div key={i} style={{
                  background: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '12px'
                }}>
                  <div style={{ 
                    color: '#aaa',
                    fontWeight: '600',
                    fontSize: '15px',
                    marginBottom: '8px'
                  }}>
                    {person.name}
                  </div>
                  <div style={{ 
                    color: '#666',
                    fontSize: '12px',
                    lineHeight: '1.5'
                  }}>
                    {person.notes}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Habits Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '24px',
          gridColumn: 'span 2'
        }}>
          <div style={{ 
            color: '#aa88ff',
            fontSize: '12px',
            fontFamily: 'Space Mono, monospace',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            🔁 Habits
            <span style={{ color: '#555', fontSize: '11px', textTransform: 'none', letterSpacing: '0' }}>
              Week {Math.ceil((Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 1)) / 86400000) + 1) / 7)} of {new Date().getFullYear()}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '20px' }}>
            {/* Apps */}
            <div style={{
              background: '#1a1a1a',
              border: '1px solid #aa88ff33',
              borderRadius: '12px',
              padding: '20px',
              textAlign: 'center'
            }}>
              <div style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '40px',
                fontWeight: '700',
                color: '#aa88ff',
                lineHeight: '1'
              }}>
                {data.habits?.apps || 0}
              </div>
              <div style={{ color: '#888', fontSize: '12px', fontFamily: 'Space Mono, monospace', marginTop: '8px' }}>
                apps shipped
              </div>
            </div>

            {/* Vlogs */}
            <div style={{
              background: '#1a1a1a',
              border: '1px solid #aa88ff33',
              borderRadius: '12px',
              padding: '20px',
              textAlign: 'center'
            }}>
              <div style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '40px',
                fontWeight: '700',
                color: '#aa88ff',
                lineHeight: '1'
              }}>
                {data.habits?.vlogs || 0}
              </div>
              <div style={{ color: '#888', fontSize: '12px', fontFamily: 'Space Mono, monospace', marginTop: '8px' }}>
                vlogs shot
              </div>
            </div>

            {/* PM */}
            <div style={{
              background: '#1a1a1a',
              border: '1px solid #aa88ff33',
              borderRadius: '12px',
              padding: '20px',
              textAlign: 'center'
            }}>
              <div style={{
                fontFamily: 'Space Mono, monospace',
                fontSize: '40px',
                fontWeight: '700',
                color: (data.habits?.pm || 0) > Math.ceil((Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 1)) / 86400000) + 1) / 7)
                  ? '#ff4444' : '#aa88ff',
                lineHeight: '1'
              }}>
                {data.habits?.pm || 0}
              </div>
              <div style={{ color: '#888', fontSize: '12px', fontFamily: 'Space Mono, monospace', marginTop: '8px' }}>
                PM count
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Footer */}
      <div style={{
        maxWidth: '1100px',
        margin: '60px auto 0',
        textAlign: 'center',
        color: '#444',
        fontSize: '13px',
        fontFamily: 'Space Mono, monospace'
      }}>
        <div>Powered by Telegram Bot + Claude API</div>
        <div style={{ marginTop: '8px', color: '#333' }}>
          Send messages to @YourDashboardBot to add entries
        </div>
      </div>
    </div>
  );
};

export default App;
