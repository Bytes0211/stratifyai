# Architecture Decision Record: CLI Interface Selection

**Date:** February 1, 2026  
**Status:** Accepted  
**Decision Makers:** scotton, Warp AI

## Context

StratumAI is a multi-provider LLM abstraction library that needs a user-facing interface. Phase 3.5 implemented a FastAPI-based web GUI with WebSocket streaming. For Phase 5, we needed to decide on the primary interface for developer usage.

## Decision

**Selected:** Rich/Typer CLI interface as the primary user interface for StratumAI

**Alternatives Considered:**
1. Continue with FastAPI web GUI as primary interface
2. Linux `dialog` utility for TUI-based interface
3. Pure bash CLI with simple prompts
4. Standard argparse CLI

## Rationale

### Why Rich/Typer CLI?

**Primary Use Case Alignment:**
- Target users are developers working in terminal environments
- Most common use case: quick LLM queries from command line
- Developers prefer terminal-based workflows (git, docker, kubectl pattern)

**Technical Advantages:**
1. **Streaming Support** - Can display real-time LLM output without flicker (critical feature)
2. **Direct Integration** - Python library access without HTTP overhead
3. **Environment Variables** - Native support via Typer (STRATUMAI_PROVIDER, STRATUMAI_MODEL)
4. **Beautiful Output** - Rich formatting for tables, colors, markdown
5. **Zero Infrastructure** - No server process needed
6. **Cross-Platform** - Works on Linux, macOS, Windows

**Developer Experience:**
- Scriptable and automatable (can pipe, chain commands)
- Copy/paste friendly output
- Tab completion support
- Inline with terminal history
- Fast startup (<1 second cold start)

### Why Not FastAPI Web GUI?

**Limitations for Developer Use:**
- Requires server process running
- HTTP overhead for local usage
- Not scriptable or pipeable
- More complex deployment
- Browser dependency
- Overhead for simple queries

**Decision:** Keep FastAPI web GUI as **optional** Phase 3.5 feature for:
- Demos and presentations
- Non-technical user access
- Remote/shared access scenarios
- Testing and debugging

### Why Not Dialog TUI?

**Limitations:**
- Cannot show streaming LLM responses
- Full-screen takeover (loses context)
- Not copy/paste friendly
- Bash/Python integration is clunky
- Dated user experience
- Limited to Linux/macOS

**Good For:** First-time setup wizards only

### Why Not Pure Bash?

**Limitations:**
- No Python library integration (would need subprocess calls)
- Complex error handling
- No type safety
- Hard to maintain
- Platform compatibility issues

## Implementation Plan

### Phase 5: CLI Interface (3-4 hours)

**Stack:**
- `typer[all]` - CLI framework (includes Rich)
- Click under the hood (environment variable support)
- Rich for formatting (tables, colors, progress)

**Commands:**
```bash
stratumai chat         # Send chat message
stratumai models       # List available models
stratumai providers    # List providers
stratumai route        # Auto-select model via router
stratumai interactive  # Interactive chat mode
```

**Features:**
- Environment variable support (STRATUMAI_PROVIDER, STRATUMAI_MODEL)
- Streaming output (plain print for LLM, Rich for metadata)
- Router integration
- Cost tracking display
- Help auto-generation
- Shell completion

### FastAPI Web GUI Status

**Retained as Optional:**
- Remains in codebase as `api/` directory
- Available via `uvicorn api.main:app`
- Documented as optional feature
- Not required for core functionality

## Consequences

### Positive
✅ Faster development workflow (terminal-native)  
✅ Better developer UX (scriptable, pipeable)  
✅ Simpler deployment (no server needed)  
✅ Direct library integration (no HTTP layer)  
✅ Beautiful output with Rich  
✅ Environment variable support  
✅ Cross-platform compatibility  

### Negative
❌ Less visual than web GUI  
❌ Not accessible to non-developers  
❌ Requires Python installation  
❌ Learning curve for CLI flags  

### Mitigated
⚠️ Interactive mode provides conversational UX  
⚠️ Rich formatting makes output beautiful  
⚠️ Help documentation auto-generated  
⚠️ Web GUI still available for non-dev users  

## Metrics for Success

**Phase 5 Completion Criteria:**
- [ ] All core commands functional (chat, models, providers, route, interactive)
- [ ] Environment variables work correctly
- [ ] Streaming displays in real-time without flicker
- [ ] Rich tables/formatting work correctly
- [ ] Interactive mode provides good UX
- [ ] Router integration seamless
- [ ] Help documentation comprehensive
- [ ] Installation takes <2 minutes

## References

- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- `docs/project-status.md` - Phase 5 task breakdown
- `WARP.md` - Updated implementation plan
- `README.md` - CLI usage examples

## Related Decisions

- **Phase 3.5:** FastAPI web GUI (retained as optional)
- **Phase 4:** Router implementation (integrates with CLI)
- **Phase 6:** Production readiness (PyPI packaging)

---

**Co-Authored-By:** Warp <agent@warp.dev>
