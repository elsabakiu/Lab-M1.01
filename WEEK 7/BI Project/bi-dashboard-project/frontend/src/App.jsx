import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import dashboardLite from "./dashboard-lite.json";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Bot, MessageCircle, Send, X } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const PRESET_QUESTIONS = [
  "Why are no-shows high on Mondays?",
  "Which providers are most overloaded?",
  "Are reminders improving attendance?",
  "What are the worst wait-time days?",
];

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-GB").format(Number(value || 0));
}

function App() {
  const [payload] = useState(dashboardLite);
  const [agentOpen, setAgentOpen] = useState(false);
  const [agentInput, setAgentInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [workflowTriggering, setWorkflowTriggering] = useState(false);
  const [workflowResult, setWorkflowResult] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, agentOpen]);

  const view = useMemo(() => buildViewModel(payload), [payload]);

  async function askQuestion(question) {
    const clean = question.trim();
    if (!clean) return;
    setAgentOpen(true);
    setMessages((current) => [...current, { role: "user", content: clean }]);
    setAgentInput("");
    setAsking(true);

    try {
      const response = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: clean }),
      });
      const result = await response.json();
      setMessages((current) => [...current, { role: "assistant", content: result }]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: {
            answer: `Sorry, I hit an error while contacting the AI agent: ${error.message}`,
            evidence: [],
            recommendation: "Check that the API server is running and try again.",
          },
        },
      ]);
    } finally {
      setAsking(false);
    }
  }

  async function triggerWorkflow() {
    setWorkflowTriggering(true);
    setWorkflowResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/workflow/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: messages.at(-1)?.role === "user"
            ? messages.at(-1).content
            : "High-risk appointment outreach from dashboard",
        }),
      });
      const result = await response.json();
      setWorkflowResult(result);
    } catch (error) {
      setWorkflowResult({
        ok: false,
        status_code: 500,
        preview: error.message,
      });
    } finally {
      setWorkflowTriggering(false);
    }
  }

  if (!payload || !view) {
    return (
      <div className="min-h-screen bg-background px-8 py-10">
        <div className="mx-auto max-w-7xl rounded-2xl border border-border bg-card p-10 shadow-soft">
          <div className="animate-pulse space-y-4">
            <div className="h-5 w-32 rounded bg-muted" />
            <div className="h-12 w-96 rounded bg-muted" />
            <div className="h-4 w-full rounded bg-muted" />
            <div className="h-4 w-3/4 rounded bg-muted" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/90 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-8 py-5">
          <div>
            <div className="section-kicker text-primary">Health AI</div>
            <h1 className="mt-1 text-4xl font-bold tracking-tight text-foreground">
              {payload.summary.title}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
              {payload.summary.subtitle}
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-8 py-6">
        <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {view.metricCards.map((card) => (
            <div key={card.label} className="metric-card">
              <div className="section-kicker">{card.label}</div>
              <div className="mt-3 text-3xl font-bold tracking-tight">{card.value}</div>
              <div
                className={`mt-3 inline-flex rounded-full px-2.5 py-1 text-[11px] font-mono ${
                  card.variant === "success"
                    ? "bg-green-50 text-success"
                    : card.variant === "warning"
                      ? "bg-amber-50 text-warning"
                      : "bg-red-50 text-destructive"
                }`}
              >
                {card.meta}
              </div>
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{card.copy}</p>
            </div>
          ))}
        </section>

        <ObservedDataTab view={view} />
      </main>

      <footer className="border-t border-border px-8 py-3 text-[10px] text-muted-foreground">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 font-mono md:flex-row md:justify-between">
          <span>{payload.summary.footer.left}</span>
          <span>{payload.summary.footer.middle}</span>
          <span>{payload.summary.footer.right}</span>
        </div>
      </footer>

      <button
        type="button"
        onClick={() => setAgentOpen((current) => !current)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-2xl shadow-cyan-500/25 transition-transform hover:scale-105"
      >
        {agentOpen ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>

      {agentOpen && (
        <div className="agent-shell fixed bottom-24 right-6 z-50 flex h-[560px] w-[400px] flex-col overflow-hidden rounded-2xl border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border bg-primary/5 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white">
                <Bot className="h-4 w-4" />
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground">Clinic Intelligence Agent</div>
                <div className="text-[10px] font-mono text-muted-foreground">
                  Ask about clinic operations &amp; data
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setAgentOpen(false)}
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div ref={scrollRef} className="chat-scroll flex-1 overflow-y-auto px-4 py-3">
            {messages.length === 0 ? (
              <div className="space-y-2">
                <p className="mb-3 text-xs text-muted-foreground">
                  Ask me anything about the clinic&apos;s operations, performance metrics, or AI opportunities:
                </p>
                {PRESET_QUESTIONS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => askQuestion(prompt)}
                    className="block w-full rounded-lg border border-border px-3 py-2 text-left text-xs text-foreground transition-colors hover:border-primary/30 hover:bg-primary/5"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((message, index) => (
                  <MessageBubble key={`${message.role}-${index}`} message={message} />
                ))}
                {asking && (
                  <div className="flex gap-2">
                    <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <Bot className="h-3 w-3 text-primary" />
                    </div>
                    <div className="rounded-xl rounded-bl-sm bg-muted px-3 py-2">
                      <div className="flex gap-1">
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/40" />
                        <span
                          className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/40"
                          style={{ animationDelay: "150ms" }}
                        />
                        <span
                          className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/40"
                          style={{ animationDelay: "300ms" }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <form
            className="flex gap-2 border-t border-border p-3"
            onSubmit={(event) => {
              event.preventDefault();
              askQuestion(agentInput);
            }}
          >
            <input
              value={agentInput}
              onChange={(event) => setAgentInput(event.target.value)}
              placeholder="Ask about clinic operations..."
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground outline-none ring-0 placeholder:text-muted-foreground"
            />
            <button
              type="submit"
              disabled={asking || !agentInput.trim()}
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

function ObservedDataTab({ view }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <ChartCard
          title="Access & Scheduling Pressure"
          subtitle="Booked appointments versus completed visits"
          badge="Core signal"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={view.dailyTrend}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: "#6b7a88" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7a88" }} />
              <Tooltip />
              <Area type="monotone" dataKey="totalAppointments" stroke="#14aab7" fill="#14aab720" />
              <Area type="monotone" dataKey="attendedAppointments" stroke="#17b26a" fill="#17b26a15" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <Card
          title="Pressure Snapshot"
          subtitle="Key access indicators for Chloe"
          badge="Summary"
          contentType="observed"
        >
          <div className="space-y-3">
            {view.pressureStats.map((stat) => (
              <div key={stat.label} className="rounded-xl border border-border p-4">
                <div className="section-kicker">{stat.label}</div>
                <div className="mt-2 text-2xl font-bold">{stat.value}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard
          title="No-show Rate by Specialty"
          subtitle="Where attendance problems are concentrated"
          badge="Risk"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.noShowBySpecialty} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <YAxis type="category" dataKey="specialty" width={110} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="noShowRate" radius={[6, 6, 6, 6]}>
                {view.noShowBySpecialty.map((entry, index) => (
                  <Cell key={index} fill={entry.noShowRate > 0.22 ? "#e55353" : "#14aab7"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Reminder Effectiveness"
          subtitle="Attendance and no-show performance by reminder status"
          badge="Operations"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.reminderSummary}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="attendanceRate" fill="#17b26a" radius={[6, 6, 0, 0]} />
              <Bar dataKey="noShowRate" fill="#e55353" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard
          title="Provider Utilization by Specialty"
          subtitle="Where staffing pressure is most uneven"
          badge="Load"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={view.providerUtilizationBySpecialty}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="specialty" tick={{ fontSize: 11 }} angle={-18} textAnchor="end" height={60} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="utilizationRate" radius={[6, 6, 0, 0]}>
                {view.providerUtilizationBySpecialty.map((entry, index) => (
                  <Cell key={index} fill={entry.utilizationRate > 0.9 ? "#e55353" : "#14aab7"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Average Lead Time by Specialty"
          subtitle="Where scheduling delay may be contributing to friction"
          badge="Access"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.leadTimeBySpecialty} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="specialty" width={110} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avgLeadTimeDays" fill="#14aab7" radius={[6, 6, 6, 6]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="No-show Heatmap — Day × Hour"
          subtitle="When the worst attendance windows happen"
          badge="Pattern"
          contentType="observed"
        >
          <HeatmapGrid rows={view.noShowHeatmapRows} />
        </Card>

        <ChartCard
          title="No-show Rate by Weekday"
          subtitle="A simpler attendance view for leadership"
          badge="Attendance"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.noShowByWeekday}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="weekday" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="noShowRate" radius={[6, 6, 0, 0]}>
                {view.noShowByWeekday.map((entry, index) => (
                  <Cell key={index} fill={entry.noShowRate > 0.2 ? "#e55353" : "#14aab7"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function AiInsightsTab({ view, onTriggerWorkflow, workflowTriggering, workflowResult }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="Main AI Takeaways"
          subtitle="The strongest current generated insights"
          badge="AI"
          contentType="ai"
        >
          <div className="space-y-3">
            {view.insights.slice(0, 4).map((insight, index) => (
              <div key={index} className="rounded-xl border border-border bg-background p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-[13px] font-semibold text-foreground">{insight.title}</div>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-mono text-primary">
                    {String(insight.priority || "priority").toUpperCase()}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{insight.finding}</p>
                <div className="mt-3 rounded-lg bg-primary/5 px-3 py-2 text-xs text-foreground">
                  <strong>Recommended action:</strong> {insight.recommended_action}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <ChartCard
          title="Risk Score Distribution"
          subtitle="How the AI layer surfaces appointment risk"
          badge="Risk layer"
          contentType="ai"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.riskDistribution}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#14aab7" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <Card
        title="High-Risk Queue"
        subtitle="Operational handoff from analytics to action"
        badge="Workflow"
        contentType="ai"
      >
        <div className="space-y-2">
          {view.riskReport.slice(0, 6).map((row, index) => (
            <div key={index} className="rounded-xl border border-border p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[13px] font-semibold text-foreground">
                    {row.Specialty} · {row.Provider}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {row.Date} at {row.Time} · patient {row["Patient ID"]}
                  </div>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-mono ${
                    row["Risk Tier"] === "High"
                      ? "bg-red-50 text-destructive"
                      : "bg-amber-50 text-warning"
                  }`}
                >
                  {row["Risk Tier"]}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card
        title="Workflow Handoff"
        subtitle="Insight -> Decision -> Workflow -> Audit trail"
        badge="n8n"
        contentType="ai"
      >
        <div className="grid gap-3 lg:grid-cols-4">
          {view.workflowHandoff.map((item) => (
            <div key={item.step} className="rounded-xl border border-border p-4">
              <div className="section-kicker">{item.step}</div>
              <div className="mt-2 text-[13px] font-semibold text-foreground">{item.title}</div>
              <div className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{item.body}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-border bg-background p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-[13px] font-semibold text-foreground">Demo the workflow handoff</div>
            <div className="mt-1 text-xs text-muted-foreground">
              Trigger the n8n proof of concept with a high-risk appointment handoff so the outreach and audit trail story is visible.
            </div>
          </div>
          <button
            type="button"
            onClick={onTriggerWorkflow}
            disabled={workflowTriggering}
            className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-white disabled:opacity-50"
          >
            {workflowTriggering ? "Triggering..." : "Trigger n8n workflow"}
          </button>
        </div>
        {workflowResult ? (
          <div className={`mt-3 rounded-xl border p-4 text-xs ${
            workflowResult.ok ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-800"
          }`}>
            <div><strong>Status:</strong> {workflowResult.status_code}</div>
            <div className="mt-1"><strong>Preview:</strong> {workflowResult.preview || "No response preview returned."}</div>
          </div>
        ) : null}
      </Card>

      <Card
        title="Latest Trace Status"
        subtitle="LangSmith visibility for the dashboard agent"
        badge="Transparency"
        contentType="ai"
      >
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-border p-4">
                <div className="section-kicker">Project</div>
                <div className="mt-2 text-sm font-semibold text-foreground">{view.monitoringStatus.project || "n/a"}</div>
                <div className="mt-1 text-xs text-muted-foreground">Shared LangSmith workspace for live traces and evaluations.</div>
              </div>
              <div className="rounded-xl border border-border p-4">
                <div className="section-kicker">Latest Experiment</div>
                <div className="mt-2 text-sm font-semibold text-foreground">{view.monitoringStatus.experiment || "not yet run"}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {view.monitoringStatus.lastRunAt ? `Last run: ${String(view.monitoringStatus.lastRunAt).replace("T", " ").replace("+00:00", " UTC")}` : "No recorded run yet."}
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-border p-4">
              <div className="section-kicker">What gets logged</div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {(view.monitoringStatus.loggedFields || []).map((item) => (
                  <div key={item} className="rounded-lg bg-background px-3 py-2 text-xs text-foreground">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-background p-4">
            <div className="section-kicker">Why this matters</div>
            <div className="mt-2 space-y-2 text-xs leading-relaxed text-muted-foreground">
              <p>Every dashboard question can be traced back to the prompt, routed analysis path, and returned output.</p>
              <p>The same project also stores evaluation runs against a fixed dataset, so Chloe can see that the AI layer is monitored rather than treated like a black box.</p>
            </div>
            <div className="mt-4 space-y-2 rounded-lg bg-card px-3 py-3 text-xs">
              <div><strong>Status:</strong> {view.monitoringStatus.tracingEnabled ? "Tracing enabled" : "Tracing disabled"}</div>
              <div><strong>Mode:</strong> {view.monitoringStatus.mode || "unknown"}</div>
              <div><strong>Dataset:</strong> {view.monitoringStatus.dataset || "n/a"}</div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

function ExecutiveTab({ view }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <ChartCard
          title="Appointment Funnel — Weekday Trend"
          subtitle="Booked vs attended visits over time, excluding Saturdays"
          badge="Trend"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={view.executiveDailyTrend}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: "#6b7a88" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7a88" }} />
              <Tooltip />
              <Area type="monotone" dataKey="totalAppointments" stroke="#14aab7" fill="#14aab720" />
              <Area type="monotone" dataKey="attendedAppointments" stroke="#17b26a" fill="#17b26a15" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <Card
          title="AI Insight Cards"
          subtitle="Suggested actions from the current data"
          badge="Action"
          contentType="ai"
        >
          <div className="space-y-3">
            {view.insights.slice(0, 3).map((insight, index) => (
              <div key={index} className="rounded-xl border border-border bg-background p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-[13px] font-semibold text-foreground">{insight.title}</div>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-mono text-primary">
                    {String(insight.priority || "priority").toUpperCase()}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{insight.finding}</p>
                <div className="mt-3 rounded-lg bg-primary/5 px-3 py-2 text-xs text-foreground">
                  <strong>Recommended action:</strong> {insight.recommended_action}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard
          title="No-show Rate by Specialty"
          subtitle="Specialty is the clearest operational cut of the data"
          badge="Risk"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.noShowBySpecialty} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <YAxis type="category" dataKey="specialty" width={110} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="noShowRate" radius={[6, 6, 6, 6]}>
                {view.noShowBySpecialty.map((entry, index) => (
                  <Cell key={index} fill={entry.noShowRate > 0.22 ? "#e55353" : "#14aab7"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Reminder Effectiveness"
          subtitle="Attendance and no-show performance by reminder status"
          badge="Operations"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.reminderSummary}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="attendanceRate" fill="#17b26a" radius={[6, 6, 0, 0]} />
              <Bar dataKey="noShowRate" fill="#e55353" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function SchedulingTab({ view }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <ChartCard
          title="Access & Scheduling Pressure"
          subtitle="Demand versus completed care"
          badge="Capacity"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={view.dailyTrend}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: "#6b7a88" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7a88" }} />
              <Tooltip />
              <Line type="monotone" dataKey="totalAppointments" stroke="#14aab7" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="attendedAppointments" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <Card
          title="Pressure Snapshot"
          subtitle="Where access friction clusters"
          badge="Summary"
          contentType="observed"
        >
          <div className="space-y-3">
            {view.pressureStats.map((stat) => (
              <div key={stat.label} className="rounded-xl border border-border p-4">
                <div className="section-kicker">{stat.label}</div>
                <div className="mt-2 text-2xl font-bold">{stat.value}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="No-show Heatmap — Day × Hour"
          subtitle="When the worst attendance windows happen"
          badge="Pattern"
          contentType="observed"
        >
          <HeatmapGrid rows={view.noShowHeatmapRows} />
        </Card>

        <ChartCard
          title="Provider Utilization by Specialty"
          subtitle="Average utilization across the clinic"
          badge="Load"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={view.providerUtilizationBySpecialty}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="specialty" tick={{ fontSize: 11 }} angle={-18} textAnchor="end" height={60} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="utilizationRate" radius={[6, 6, 0, 0]}>
                {view.providerUtilizationBySpecialty.map((entry, index) => (
                  <Cell key={index} fill={entry.utilizationRate > 0.9 ? "#e55353" : "#14aab7"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard
          title="Average Lead Time by Specialty"
          subtitle="Days from booking to appointment"
          badge="Access"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.leadTimeBySpecialty} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="specialty" width={110} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avgLeadTimeDays" fill="#14aab7" radius={[6, 6, 6, 6]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="No-show Rate by Weekday"
          subtitle="A simpler attendance view for leadership"
          badge="Attendance"
          contentType="observed"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.noShowByWeekday}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="weekday" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(value) => `${Math.round(value * 100)}%`} />
              <Tooltip formatter={(value) => formatPercent(value)} />
              <Bar dataKey="noShowRate" radius={[6, 6, 0, 0]}>
                {view.noShowByWeekday.map((entry, index) => (
                  <Cell key={index} fill={entry.noShowRate > 0.2 ? "#e55353" : "#14aab7"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function ImpactTab({ view, onTriggerWorkflow, workflowTriggering, workflowResult }) {
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const scenario = view.impactScenarios[scenarioIndex];

  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="AI Opportunities & Impact"
          subtitle="What to pilot first and why"
          badge="AI"
          contentType="ai"
        >
          <div className="space-y-3">
            {view.impactHighlights.map((item) => (
              <div key={item.label} className="rounded-xl border border-border p-4">
                <div className="section-kicker">{item.label}</div>
                <div className="mt-2 text-2xl font-bold">{item.value}</div>
                <div className="mt-2 text-xs leading-relaxed text-muted-foreground">{item.copy}</div>
              </div>
            ))}
          </div>
        </Card>

        <ChartCard
          title="Risk Score Distribution"
          subtitle="How the AI risk layer surfaces appointment risk"
          badge="Monitoring"
          contentType="ai"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={view.riskDistribution}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#14aab7" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="dashboard-card">
        <div className="mb-4">
          <div className="section-kicker">AI Impact Simulation</div>
          <div className="mt-1 text-[13px] font-semibold text-foreground">Select a Scenario</div>
        </div>
        <div className="mb-4 grid gap-3 md:grid-cols-3">
          {view.impactScenarios.map((item, index) => (
            <button
              key={item.title}
              type="button"
              onClick={() => setScenarioIndex(index)}
              className={`rounded-xl border p-4 text-left transition-all ${
                scenarioIndex === index
                  ? "border-primary/40 bg-primary/5 shadow-soft"
                  : "border-border bg-card hover:border-primary/30"
              }`}
            >
              <div className="text-xl">{item.icon}</div>
              <div className="mt-2 text-[13px] font-semibold text-foreground">
                {item.title.replace("Scenario: ", "")}
              </div>
              <div className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{item.subtitle}</div>
              <span className="mt-2 inline-block rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-mono text-primary">
                {item.tag}
              </span>
            </button>
          ))}
        </div>

        <ChartCard
          title={scenario.title}
          subtitle="Estimated business value over 12 months"
          badge="ROI"
          contentType="modeled"
        >
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={scenario.points}>
              <CartesianGrid stroke="#e5edf3" strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} angle={-18} textAnchor="end" height={70} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {scenario.points.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Card
          title="Use Case Comparison"
          subtitle="Key parameters at a glance"
          badge="Decision"
          contentType="modeled"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {["Use Case", "AI Type", "PHI Risk", "ROI Speed", "Cost/mo"].map((header) => (
                    <th
                      key={header}
                      className="px-2.5 py-2.5 text-left text-[10px] font-normal uppercase tracking-wider text-muted-foreground"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {view.useCaseComparison.map((row) => (
                  <tr key={row.useCase} className="border-b border-border/60">
                    <td className="px-2.5 py-2.5 font-medium text-foreground">{row.useCase}</td>
                    <td className="px-2.5 py-2.5 text-muted-foreground">{row.aiType}</td>
                    <td className="px-2.5 py-2.5 text-muted-foreground">{row.phiRisk}</td>
                    <td className="px-2.5 py-2.5 text-muted-foreground">{row.roiSpeed}</td>
                    <td className="px-2.5 py-2.5 text-muted-foreground">{row.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card
          title="High-Risk Queue"
          subtitle="Operational handoff from analytics to action"
          badge="Workflow"
          contentType="ai"
        >
          <div className="space-y-2">
            {view.riskReport.slice(0, 6).map((row, index) => (
              <div key={index} className="rounded-xl border border-border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[13px] font-semibold text-foreground">
                      {row.Specialty} · {row.Provider}
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      {row.Date} at {row.Time} · patient {row["Patient ID"]}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-mono ${
                      row["Risk Tier"] === "High"
                        ? "bg-red-50 text-destructive"
                        : "bg-amber-50 text-warning"
                    }`}
                  >
                    {row["Risk Tier"]}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="Workflow Handoff"
        subtitle="Insight -> Decision -> Workflow -> Audit trail"
        badge="n8n"
        contentType="ai"
      >
        <div className="grid gap-3 lg:grid-cols-4">
          {view.workflowHandoff.map((item) => (
            <div key={item.step} className="rounded-xl border border-border p-4">
              <div className="section-kicker">{item.step}</div>
              <div className="mt-2 text-[13px] font-semibold text-foreground">{item.title}</div>
              <div className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{item.body}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-border bg-background p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-[13px] font-semibold text-foreground">Demo the workflow handoff</div>
            <div className="mt-1 text-xs text-muted-foreground">
              Trigger the n8n proof of concept with a high-risk appointment handoff so the outreach and audit trail story is visible.
            </div>
          </div>
          <button
            type="button"
            onClick={onTriggerWorkflow}
            disabled={workflowTriggering}
            className="rounded-lg bg-primary px-4 py-2 text-xs font-medium text-white disabled:opacity-50"
          >
            {workflowTriggering ? "Triggering..." : "Trigger n8n workflow"}
          </button>
        </div>
        {workflowResult ? (
          <div className={`mt-3 rounded-xl border p-4 text-xs ${
            workflowResult.ok ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-800"
          }`}>
            <div><strong>Status:</strong> {workflowResult.status_code}</div>
            <div className="mt-1"><strong>Preview:</strong> {workflowResult.preview || "No response preview returned."}</div>
          </div>
        ) : null}
      </Card>

      <Card
        title="Latest Trace Status"
        subtitle="Live LangSmith visibility for the dashboard agent"
        badge="LangSmith"
        contentType="ai"
      >
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-border p-4">
                <div className="section-kicker">Project</div>
                <div className="mt-2 text-sm font-semibold text-foreground">{view.monitoringStatus.project || "n/a"}</div>
                <div className="mt-1 text-xs text-muted-foreground">Shared LangSmith workspace for live traces and evaluations.</div>
              </div>
              <div className="rounded-xl border border-border p-4">
                <div className="section-kicker">Latest Experiment</div>
                <div className="mt-2 text-sm font-semibold text-foreground">{view.monitoringStatus.experiment || "not yet run"}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {view.monitoringStatus.lastRunAt ? `Last run: ${String(view.monitoringStatus.lastRunAt).replace("T", " ").replace("+00:00", " UTC")}` : "No recorded run yet."}
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-border p-4">
              <div className="section-kicker">What gets logged</div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {(view.monitoringStatus.loggedFields || []).map((item) => (
                  <div key={item} className="rounded-lg bg-background px-3 py-2 text-xs text-foreground">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-background p-4">
            <div className="section-kicker">Why this matters</div>
            <div className="mt-2 space-y-2 text-xs leading-relaxed text-muted-foreground">
              <p>Every dashboard question can be traced back to the prompt, routed analysis path, and returned output.</p>
              <p>The same project also stores evaluation runs against a fixed dataset, so Chloe can see that the AI layer is monitored rather than treated like a black box.</p>
            </div>
            <div className="mt-4 space-y-2 rounded-lg bg-card px-3 py-3 text-xs">
              <div><strong>Status:</strong> {view.monitoringStatus.tracingEnabled ? "Tracing enabled" : "Tracing disabled"}</div>
              <div><strong>Mode:</strong> {view.monitoringStatus.mode || "unknown"}</div>
              <div><strong>Dataset:</strong> {view.monitoringStatus.dataset || "n/a"}</div>
            </div>
          </div>
        </div>
      </Card>

      <Card
        title="Transparency, Monitoring & Human Oversight"
        subtitle="What makes the AI approach safe and inspectable"
        badge="Trust"
        contentType="modeled"
      >
        <div className="grid gap-3 md:grid-cols-4">
          {view.oversightCards.map((card) => (
            <div
              key={card.title}
              className={`rounded-xl border border-border border-l-[3px] p-4 ${
                card.variant === "teal"
                  ? "border-l-primary bg-primary/5"
                  : card.variant === "green"
                    ? "border-l-success bg-green-50"
                    : card.variant === "amber"
                      ? "border-l-warning bg-amber-50"
                      : "border-l-purple bg-purple/5"
              }`}
            >
              <div className="mb-2.5 text-2xl">{card.icon}</div>
              <div className="text-[13px] font-semibold text-foreground">{card.title}</div>
              <div className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{card.body}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Card({ title, subtitle, children, badge, contentType }) {
  return (
    <div className="dashboard-card">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="text-[13px] font-semibold text-foreground">{title}</div>
          <div className="mt-0.5 text-[11px] font-mono text-muted-foreground">{subtitle}</div>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {contentType ? (
            <span className={`card-badge border ${CONTENT_TYPE_STYLES[contentType]}`}>
              {CONTENT_TYPE_LABELS[contentType]}
            </span>
          ) : null}
          {badge ? <span className="card-badge border-primary/20 bg-primary/5 text-primary">{badge}</span> : null}
        </div>
      </div>
      {children}
    </div>
  );
}

function ChartCard({ title, subtitle, children, badge, contentType }) {
  return <Card title={title} subtitle={subtitle} badge={badge} contentType={contentType}>{children}</Card>;
}

function HeatmapGrid({ rows }) {
  const hours = rows[0]?.values.map((item) => item.hour) || [];
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[640px] gap-2" style={{ gridTemplateColumns: `140px repeat(${hours.length}, minmax(38px, 1fr))` }}>
        <div />
        {hours.map((hour) => (
          <div key={hour} className="text-center text-[10px] font-mono text-muted-foreground">
            {hour}
          </div>
        ))}
        {rows.map((row) => (
          <FragmentRow key={row.weekday} row={row} />
        ))}
      </div>
    </div>
  );
}

function FragmentRow({ row }) {
  return (
    <>
      <div className="flex items-center text-xs font-medium text-foreground">{row.weekday}</div>
      {row.values.map((cell) => (
        <div
          key={`${row.weekday}-${cell.hour}`}
          className="flex h-10 items-center justify-center rounded-lg text-[10px] font-mono text-foreground"
          style={{
            background: cell.color,
            color: cell.rate > 0.2 ? "#ffffff" : "#213547",
          }}
          title={`${row.weekday} ${cell.hour}: ${formatPercent(cell.rate)}`}
        >
          {Math.round(cell.rate * 100)}%
        </div>
      ))}
    </>
  );
}

function MessageBubble({ message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[85%] rounded-xl rounded-br-sm bg-primary px-3 py-2 text-xs leading-relaxed text-white">
          {message.content}
        </div>
      </div>
    );
  }

  const result = message.content;
  return (
    <div className="flex gap-2">
      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-primary/10">
        <Bot className="h-3 w-3 text-primary" />
      </div>
      <div className="max-w-[85%] rounded-xl rounded-bl-sm bg-muted px-3 py-2 text-xs leading-relaxed text-foreground">
        <div className="prose prose-xs max-w-none">
          <ReactMarkdown>{result.answer}</ReactMarkdown>
        </div>
        {result.evidence?.length ? (
          <div className="mt-3">
            <div className="text-[10px] font-mono uppercase tracking-[2px] text-muted-foreground">
              Evidence
            </div>
            <ul className="mt-1 space-y-1 text-[11px] text-muted-foreground">
              {result.evidence.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {result.recommendation ? (
          <div className="mt-3 rounded-lg bg-card px-3 py-2 text-[11px]">
            <strong>Recommended action:</strong> {result.recommendation}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function buildViewModel(payload) {
  if (!payload) return null;

  const dailyKpis = payload.datasets.dailyKpis || [];
  const noShowPatterns = payload.datasets.noShowPatterns || [];
  const providerUtilization = payload.datasets.providerUtilization || [];
  const reminderEffectiveness = payload.datasets.reminderEffectiveness || [];
  const appointments = payload.datasets.appointments || [];
  const riskReport = payload.datasets.riskReport || [];
  const insights = payload.datasets.insights || [];
  const facts = payload.facts || {};

  const dailyTrend = dailyKpis.map((row) => ({
    ...row,
    dateLabel: String(row.date).slice(5),
    totalAppointments: Number(row.total_appointments),
    attendedAppointments: Number(row.attended_appointments),
    noShowRate: Number(row.no_show_rate),
    avgWaitTime: Number(row.avg_wait_time_min),
  })).filter((row) => row.date !== "2016-05-14");
  const executiveDailyTrend = dailyTrend.filter((row) => row.date !== "2016-05-14");

  const bySpecialty = aggregate(noShowPatterns, "specialty", ["no_show_count", "total_appointments"]).map((row) => ({
    specialty: row.specialty,
    noShowRate: row.no_show_count / row.total_appointments,
  })).sort((a, b) => b.noShowRate - a.noShowRate);

  const reminderSummary = aggregate(reminderEffectiveness, "reminder_status", [
    "attended_appointments",
    "no_show_appointments",
    "total_appointments",
  ]).map((row) => ({
    label: row.reminder_status === "Reminder Sent" ? "Reminder Sent" : "No Reminder",
    attendanceRate: row.attended_appointments / row.total_appointments,
    noShowRate: row.no_show_appointments / row.total_appointments,
  }));

  const pressureStats = [
    {
      label: "Average lead time",
      value: `${average(appointments, "lead_time_days").toFixed(1)} days`,
    },
    {
      label: "Overloaded provider-days",
      value: formatNumber(providerUtilization.filter((row) => row.utilization_status === "Overloaded").length),
    },
    {
      label: "Average utilization",
      value: formatPercent(average(providerUtilization, "utilization_rate")),
    },
  ];

  const leadTimeBySpecialty = aggregate(appointments, "specialty", ["lead_time_days", "appointment_id"], {
    appointment_id: "count",
  }).map((row) => ({
    specialty: row.specialty,
    avgLeadTimeDays: row.lead_time_days / row.appointment_id,
  })).sort((a, b) => b.avgLeadTimeDays - a.avgLeadTimeDays);

  const noShowByWeekday = aggregate(noShowPatterns, "weekday", ["no_show_count", "total_appointments"]).map((row) => ({
    weekday: row.weekday,
    noShowRate: row.no_show_count / row.total_appointments,
  }));

  const providerUtilizationBySpecialty = aggregate(
    providerUtilization,
    "specialty",
    ["utilization_rate", "date"],
    { date: "count" }
  ).map((row) => ({
    specialty: row.specialty,
    utilizationRate: row.utilization_rate / row.date,
  }));

  const heatmapOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const heatmapMap = new Map();
  noShowPatterns.forEach((row) => {
    const key = `${row.weekday}__${row.hour}`;
    const current = heatmapMap.get(key) || { total: 0, count: 0 };
    current.total += Number(row.no_show_rate);
    current.count += 1;
    heatmapMap.set(key, current);
  });
  const hours = Array.from(new Set(noShowPatterns.map((row) => Number(row.hour)))).sort((a, b) => a - b);
  const noShowHeatmapRows = heatmapOrder.map((weekday) => ({
    weekday,
    values: hours.map((hour) => {
      const key = `${weekday}__${hour}`;
      const current = heatmapMap.get(key);
      const rate = current ? current.total / current.count : 0;
      return {
        hour,
        rate,
        color:
          rate > 0.25
            ? "#e55353"
            : rate > 0.2
              ? "#f59e0b"
              : rate > 0.15
                ? "#a7e3e8"
                : "#edf8fa",
      };
    }),
  }));

  const metricCards = [
    {
      label: "No-show rate",
      value: formatPercent(facts.no_show?.overall_no_show_rate),
      meta: `Peak day ${formatPercent(facts.no_show?.peak_no_show_rate)}`,
      copy: "Headline indicator for scheduling friction and missed revenue.",
      variant: "danger",
    },
    {
      label: "Average wait time",
      value: `${Number(facts.wait_times?.average_wait_time_min || 0).toFixed(1)} min`,
      meta: `${facts.wait_times?.anomalous_days_count || 0} high-delay days`,
      copy: "Long waits usually signal provider overload and demand clustering.",
      variant: "warning",
    },
    {
      label: "Overloaded provider share",
      value: formatPercent(facts.provider_utilization?.overloaded_share),
      meta: `Top strain ${facts.provider_utilization?.top_overloaded_specialty || "n/a"}`,
      copy: "The fastest read on whether clinic capacity is balanced or brittle.",
      variant: "warning",
    },
    {
      label: "Reminder gap",
      value: formatPercent(Math.abs(Number(facts.reminder_effectiveness?.reminder_effect_size || 0))),
      meta: `With reminder ${formatPercent(facts.reminder_effectiveness?.reminder_sent_no_show_rate)}`,
      copy: "Compare targeting strategy before assuming reminders are driving the outcome.",
      variant: "success",
    },
  ];

  const riskDistribution = buildRiskDistribution(riskReport);

  const impactHighlights = [
    {
      label: "High-risk appointments today",
      value: formatNumber(riskReport.filter((row) => row["Risk Tier"] === "High").length),
      copy: "Appointments the AI layer would elevate for human review or proactive outreach.",
    },
    {
      label: "Monitored evaluation cases",
      value: "15",
      copy: "LangSmith traces and evaluations make the system observable, not opaque.",
    },
    {
      label: "Automation readiness",
      value: "Workflow ready",
      copy: "The n8n flow can take insights into reminders and follow-up actions.",
    },
  ];

  return {
    metricCards,
    dailyTrend,
    executiveDailyTrend,
    noShowBySpecialty: bySpecialty,
    reminderSummary,
    pressureStats,
    leadTimeBySpecialty,
    noShowByWeekday,
    providerUtilizationBySpecialty,
    noShowHeatmapRows,
    riskDistribution,
    riskReport,
    insights,
    impactScenarios: payload.content.impactScenarios || [],
    useCaseComparison: payload.content.useCaseComparison || [],
    workflowHandoff: payload.content.workflowHandoff || [],
    monitoringStatus: payload.content.monitoringStatus || {},
    oversightCards: payload.content.oversightCards || [],
    impactHighlights,
  };
}

function aggregate(rows, key, valueFields, transforms = {}) {
  const map = new Map();
  rows.forEach((row) => {
    const bucket = map.get(row[key]) || { [key]: row[key] };
    valueFields.forEach((field) => {
      const mode = transforms[field] || "sum";
      if (mode === "count") {
        bucket[field] = (bucket[field] || 0) + 1;
      } else {
        bucket[field] = (bucket[field] || 0) + Number(row[field] || 0);
      }
    });
    map.set(row[key], bucket);
  });
  return Array.from(map.values());
}

function average(rows, field) {
  if (!rows.length) return 0;
  return rows.reduce((sum, row) => sum + Number(row[field] || 0), 0) / rows.length;
}

function buildRiskDistribution(rows) {
  const buckets = [
    { bucket: "0.0-0.2", min: 0, max: 0.2, count: 0 },
    { bucket: "0.2-0.4", min: 0.2, max: 0.4, count: 0 },
    { bucket: "0.4-0.6", min: 0.4, max: 0.6, count: 0 },
    { bucket: "0.6-0.8", min: 0.6, max: 0.8, count: 0 },
    { bucket: "0.8-1.0", min: 0.8, max: 1.01, count: 0 },
  ];
  rows.forEach((row) => {
    const risk = Number(row["No-Show Risk"] || 0);
    const bucket = buckets.find((item) => risk >= item.min && risk < item.max);
    if (bucket) bucket.count += 1;
  });
  return buckets;
}

export default App;
