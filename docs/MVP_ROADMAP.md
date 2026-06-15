# AgentScope MVP Roadmap

## Phase 1: Core Analysis Engine (Week 1–2) ✅

- [x] Canonical trace schema definition
- [x] Multi-format trace parsers (Generic, LangGraph, CrewAI)
- [x] Loop detection (consecutive + cyclic patterns)
- [x] Tool usage analysis
- [x] Cost/token analysis
- [x] Reasoning redundancy detection (TF-IDF)
- [x] Hallucinated tool detection
- [x] Health scoring algorithm
- [x] FastAPI REST API

## Phase 2: Dashboard & Visualization (Week 3) ✅

- [x] Next.js frontend with Tailwind
- [x] Trace upload (drag-and-drop)
- [x] Health score display
- [x] Issues & strengths report
- [x] Tool usage bar chart (Plotly)
- [x] Cost breakdown pie chart (Plotly)
- [x] Agent execution timeline
- [x] Failure/workflow graph (React Flow)

## Phase 3: Polish & Portfolio (Week 4)

- [ ] Docker Compose deployment
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Unit tests for all analyzers (>80% coverage)
- [ ] Integration tests for API
- [ ] Sample traces for each framework
- [ ] Architecture diagram in README
- [ ] Demo video / GIF

## Phase 4: Stretch Goals

| Feature | Priority | Effort |
|---------|----------|--------|
| LangGraph native integration (live trace capture) | High | 2 weeks |
| OpenAI Agents SDK integration | High | 1 week |
| CrewAI native integration | Medium | 1 week |
| Trace persistence (PostgreSQL) | Medium | 1 week |
| Multi-agent collaboration analysis | Medium | 2 weeks |
| Failure pattern classification (ML) | Low | 3 weeks |
| Agent benchmarking leaderboard | Low | 2 weeks |
| Cost prediction before execution | Low | 2 weeks |
| Optimization recommendations engine | Medium | 2 weeks |
| Trace replay mode | Low | 3 weeks |

## Development Milestones

### Milestone 1: "It Works" (End of Week 2)
- Upload a JSON trace → get a health report via API
- All 5 analyzers produce meaningful output
- Sample trace demonstrates all issue types

### Milestone 2: "It Looks Good" (End of Week 3)
- Full dashboard with all visualizations
- Responsive design, dark theme
- Upload → report in <3 seconds for typical traces

### Milestone 3: "Portfolio Ready" (End of Week 4)
- Deployed demo URL
- README with architecture, screenshots, quickstart
- 3+ sample traces (healthy, degraded, failing agent)
- Test suite passing in CI

### Milestone 4: "Production Ready" (Future)
- Authentication & multi-tenancy
- Trace storage & history
- Webhook integrations
- SDK for programmatic trace submission

## Success Metrics

| Metric | Target |
|--------|--------|
| Analysis latency (100-step trace) | < 2s |
| Loop detection accuracy | > 95% on test set |
| Redundancy detection threshold | Configurable (default 0.7) |
| Health score correlation with human judgment | > 0.8 Spearman |
