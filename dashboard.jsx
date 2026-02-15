import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { createClient } from '@supabase/supabase-js';

// Supabase configuration - Replace with your actual values
const supabase = createClient(
  'YOUR_SUPABASE_URL',  // e.g., 'https://xxxxx.supabase.co'
  'YOUR_SUPABASE_ANON_KEY'  // Your anon/public key
);

// Utility to generate sample data
const generateSampleData = () => ({
  finance: [
    // January
    { date: '1/2', fullDate: '2026-01-02', amount: 134, category: 'groceries' },
    { date: '1/5', fullDate: '2026-01-05', amount: 89, category: 'dining' },
    { date: '1/8', fullDate: '2026-01-08', amount: 45, category: 'transport' },
    { date: '1/10', fullDate: '2026-01-10', amount: 156, category: 'groceries' },
    { date: '1/12', fullDate: '2026-01-12', amount: 78, category: 'dining' },
    { date: '1/15', fullDate: '2026-01-15', amount: 234, category: 'groceries' },
    { date: '1/18', fullDate: '2026-01-18', amount: 92, category: 'entertainment' },
    { date: '1/20', fullDate: '2026-01-20', amount: 67, category: 'dining' },
    { date: '1/23', fullDate: '2026-01-23', amount: 145, category: 'groceries' },
    { date: '1/25', fullDate: '2026-01-25', amount: 54, category: 'transport' },
    { date: '1/28', fullDate: '2026-01-28', amount: 89, category: 'dining' },
    { date: '1/30', fullDate: '2026-01-30', amount: 178, category: 'groceries' },
    
    // February (current)
    { date: '2/2', fullDate: '2026-02-02', amount: 198, category: 'groceries' },
    { date: '2/4', fullDate: '2026-02-04', amount: 76, category: 'dining' },
    { date: '2/7', fullDate: '2026-02-07', amount: 145, category: 'groceries' },
    { date: '2/8', fullDate: '2026-02-08', amount: 52, category: 'dining' },
    { date: '2/9', fullDate: '2026-02-09', amount: 89, category: 'transport' },
    { date: '2/10', fullDate: '2026-02-10', amount: 220, category: 'groceries' },
    { date: '2/11', fullDate: '2026-02-11', amount: 75, category: 'dining' },
    { date: '2/12', fullDate: '2026-02-12', amount: 45, category: 'entertainment' },
    { date: '2/13', fullDate: '2026-02-13', amount: 67, category: 'dining' },
    
    // December (for 3-month view)
    { date: '12/5', fullDate: '2025-12-05', amount: 156, category: 'groceries' },
    { date: '12/8', fullDate: '2025-12-08', amount: 92, category: 'dining' },
    { date: '12/12', fullDate: '2025-12-12', amount: 234, category: 'groceries' },
    { date: '12/15', fullDate: '2025-12-15', amount: 67, category: 'transport' },
    { date: '12/18', fullDate: '2025-12-18', amount: 145, category: 'entertainment' },
    { date: '12/20', fullDate: '2025-12-20', amount: 89, category: 'dining' },
    { date: '12/23', fullDate: '2025-12-23', amount: 178, category: 'groceries' },
    { date: '12/27', fullDate: '2025-12-27', amount: 234, category: 'dining' },
    { date: '12/30', fullDate: '2025-12-30', amount: 123, category: 'groceries' }
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
    { task: 'Q1 performance review', due: '2/18', priority: 'high' },
    { task: 'Dentist appointment', due: '2/21', priority: 'medium' },
    { task: 'File taxes', due: '3/15', priority: 'high' }
  ]
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

    entries.forEach(entry => {
      // Parse data if it's a string (bot saves as JSON string)
      const data = typeof entry.data === 'string' ? JSON.parse(entry.data) : entry.data;
      
      if (entry.category === 'finance') {
        const date = new Date(data.date || entry.created_at);
        finance.push({
          date: `${date.getMonth() + 1}/${date.getDate()}`,
          fullDate: data.date || entry.created_at,
          amount: Math.abs(data.amount || 0), // Use absolute value for display
          category: data.subcategory || data.description || 'other'
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
        todos.push({
          task: data.task || 'Task',
          due: data.due || 'TBD',
          priority: data.priority || 'medium',
          status: data.status || 'pending'
        });
      }
    });

    return { finance, dating, todos };
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
      `}</style>

      {/* Header */}
      <div style={{ maxWidth: '1400px', margin: '0 auto 60px' }}>
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
          fontSize: '24px',
          fontWeight: '800',
          color: '#ffffff',
          margin: '0 0 8px 0',
          letterSpacing: '-1px'
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
        maxWidth: '1400px', 
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '24px'
      }}>
        
        {/* Finance Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '32px',
          position: 'relative',
          overflow: 'hidden'
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
              💰 Finance
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
            <BarChart data={filteredFinance.slice(-20)}>
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

        {/* Dating Widget - Now larger with 3 lists */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '32px',
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

        {/* Todos Widget */}
        <div className="widget" style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #222 100%)',
          border: '1px solid #333',
          borderRadius: '16px',
          padding: '32px'
        }}>
          <div style={{ 
            color: '#88ff00',
            fontSize: '12px',
            fontFamily: 'Space Mono, monospace',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            marginBottom: '20px'
          }}>
            ✅ To-Do
          </div>

          {data.todos.map((todo, i) => (
            <div key={i} style={{
              background: '#1a1a1a',
              border: todo.priority === 'high' ? '1px solid #88ff0044' : '1px solid #2a2a2a',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              opacity: todo.status === 'done' ? 0.5 : 1
            }}>
              <div style={{
                width: '20px',
                height: '20px',
                border: '2px solid #444',
                borderRadius: '6px',
                flexShrink: 0,
                background: todo.status === 'done' ? '#88ff00' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#000',
                fontSize: '14px'
              }}>
                {todo.status === 'done' && '✓'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ 
                  color: '#fff',
                  fontSize: '14px',
                  marginBottom: '4px',
                  textDecoration: todo.status === 'done' ? 'line-through' : 'none'
                }}>
                  {todo.task}
                </div>
                <div style={{ 
                  color: '#666',
                  fontSize: '12px',
                  fontFamily: 'Space Mono, monospace'
                }}>
                  Due: {todo.due} • {todo.status}
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>

      {/* Footer */}
      <div style={{
        maxWidth: '1400px',
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
