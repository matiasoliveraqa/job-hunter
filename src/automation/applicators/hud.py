"""
HUD overlay and field highlight mixin for Playwright browser view.
"""


class HudMixin:
    """Manages visual status banners and DOM element indicators in the browser."""

    async def show_hud_status(self, message: str, status: str = "thinking", auto_hide_ms: int = 0) -> None:
        """Inject or update a modern floating HUD indicator in the browser view."""
        try:
            await self.page.evaluate(
                """({ message, status, autoHideMs }) => {
                    let hud = document.getElementById('jh-ai-hud');
                    if (!hud) {
                        hud = document.createElement('div');
                        hud.id = 'jh-ai-hud';
                        hud.style.position = 'fixed';
                        hud.style.top = '16px';
                        hud.style.right = '20px';
                        hud.style.zIndex = '9999999';
                        hud.style.display = 'flex';
                        hud.style.alignItems = 'center';
                        hud.style.gap = '10px';
                        hud.style.padding = '10px 16px';
                        hud.style.borderRadius = '10px';
                        hud.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                        hud.style.fontSize = '13px';
                        hud.style.fontWeight = '500';
                        hud.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)';
                        hud.style.transition = 'all 0.3s ease';
                        hud.style.pointerEvents = 'none';
                        document.body.appendChild(hud);
                    }
                    hud.style.opacity = '1';
                    hud.style.transform = 'translateY(0)';

                    if (status === 'thinking') {
                        hud.style.background = 'rgba(15, 23, 42, 0.94)';
                        hud.style.backdropFilter = 'blur(8px)';
                        hud.style.border = '1px solid rgba(99, 102, 241, 0.6)';
                        hud.style.color = '#f8fafc';
                        hud.innerHTML = `
                            <div style="width: 14px; height: 14px; border: 2px solid #818cf8; border-top-color: transparent; border-radius: 50%; animation: jh-spin 0.8s linear infinite;"></div>
                            <span>${message}</span>
                            <style>
                                @keyframes jh-spin { to { transform: rotate(360deg); } }
                                @keyframes jh-pulse-border {
                                    0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.6); }
                                    70% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
                                    100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
                                }
                            </style>
                        `;
                    } else if (status === 'success') {
                        hud.style.background = 'rgba(15, 23, 42, 0.94)';
                        hud.style.backdropFilter = 'blur(8px)';
                        hud.style.border = '1px solid rgba(34, 197, 94, 0.6)';
                        hud.style.color = '#86efac';
                        hud.innerHTML = `<span style="font-weight: 700; color: #4ade80;">✓</span><span>${message}</span>`;
                    } else if (status === 'warning') {
                        hud.style.background = 'rgba(15, 23, 42, 0.94)';
                        hud.style.backdropFilter = 'blur(8px)';
                        hud.style.border = '1px solid rgba(234, 179, 8, 0.7)';
                        hud.style.color = '#fef08a';
                        hud.innerHTML = `<span style="font-weight: 700; color: #eab308;">⚠</span><span>${message}</span>`;
                    }

                    if (autoHideMs > 0) {
                        setTimeout(() => {
                            if (hud) {
                                hud.style.opacity = '0';
                                hud.style.transform = 'translateY(-6px)';
                            }
                        }, autoHideMs);
                    }
                }""",
                {"message": message, "status": status, "autoHideMs": auto_hide_ms},
            )
        except Exception:
            pass

    async def hide_hud_status(self) -> None:
        """Fade out and remove the HUD indicator."""
        try:
            await self.page.evaluate(
                """() => {
                    const hud = document.getElementById('jh-ai-hud');
                    if (hud) {
                        hud.style.opacity = '0';
                        hud.style.transform = 'translateY(-6px)';
                        setTimeout(() => hud.remove(), 400);
                    }
                }"""
            )
        except Exception:
            pass

    async def highlight_field_thinking(self, el, placeholder_text: str = "Job Hunter AI drafting answer...") -> None:
        """Highlight active input/textarea and set temporary placeholder."""
        try:
            await el.scroll_into_view_if_needed()
            await el.evaluate(
                """(node, ph) => {
                    node.setAttribute('data-jh-orig-border', node.style.border || '');
                    node.setAttribute('data-jh-orig-ph', node.getAttribute('placeholder') || '');
                    node.style.border = '2px solid #6366f1';
                    node.style.outline = 'none';
                    node.style.animation = 'jh-pulse-border 1.5s infinite';
                    if (ph) node.setAttribute('placeholder', ph);
                }""",
                placeholder_text,
            )
        except Exception:
            pass

    async def clear_field_highlight(self, el) -> None:
        """Restore original border and placeholder of an input/textarea."""
        try:
            await el.evaluate(
                """(node) => {
                    const origB = node.getAttribute('data-jh-orig-border') || '';
                    const origPh = node.getAttribute('data-jh-orig-ph') || '';
                    node.style.border = origB;
                    node.style.animation = '';
                    if (origPh) node.setAttribute('placeholder', origPh);
                }"""
            )
        except Exception:
            pass
