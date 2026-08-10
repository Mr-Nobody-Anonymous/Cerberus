"""Menu AI Processing Mixin — AI, Orchestrator & Brain processing logic.

Extracted from menu.py to reduce God object size.
Contains: _process_with_ai, orchestrator/brain fallback, step execution,
          approval flow, target extraction, command execution, result display.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from rich.prompt import Prompt

if TYPE_CHECKING:
    from core.execution.execution_engine import ExecutionResult
    from core.ui._menu_protocol import MenuProtocol

    _MixinBase = MenuProtocol
else:
    _MixinBase = object


class MenuAIProcessingMixin(_MixinBase):
    """AI / Orchestrator processing methods for DrakbenMenu."""

    # ── AI entry point ──────────────────────────────────────────────

    def _process_with_ai(self, user_input: str) -> None:
        """Process with AI using the new orchestrator."""
        lang: str = self.config.language

        # ====== DOĞAL DİLDEN HEDEF ÇIKARMA ======
        extracted_target = self._extract_target_from_text(user_input)
        if extracted_target and not self.config.target:
            self.config.target = extracted_target
            if self.orchestrator:
                self.orchestrator.set_target(extracted_target)
            self.console.print(
                f"[bold green]Hedef ayarlandı: {extracted_target}[/]",
            )

        # Use orchestrator if available
        if self.orchestrator:
            self._process_with_orchestrator(user_input, lang)
            return

        # Fallback to old brain if orchestrator not available
        self._process_with_brain_fallback(user_input, lang)

    # ── Orchestrator path ───────────────────────────────────────────

    def _process_with_orchestrator(self, user_input: str, lang: str) -> None:
        """Process input using the new orchestrator."""
        thinking = "İşleniyor..." if lang == "tr" else "Processing..."

        try:
            target_before = self.config.target

            with self.console.status(f"[bold {self.COLORS['purple']}]{thinking}"):
                self.orchestrator.context.language = lang
                result = self.orchestrator.chat(user_input)

            self._sync_orchestrator_target(target_before)
            self._display_orchestrator_result(result, lang)

        except KeyboardInterrupt:
            cancel_msg = "Iptal edildi." if lang == "tr" else "Cancelled."
            self.console.print(f"\n[yellow]{cancel_msg}[/]")

    def _sync_orchestrator_target(self, target_before: str | None) -> None:
        """Sync orchestrator-discovered target to config."""
        new_target = self.orchestrator.context.target
        if new_target and new_target != target_before:
            self.config_manager.set_target(new_target)
            self.config = self.config_manager.config
            self.console.print(f"\n[bold green]Hedef ayarlandi: {new_target}[/]")

    def _display_orchestrator_result(self, result: dict, lang: str) -> None:
        """Display the orchestrator chat result."""
        if result.get("success"):
            response = result.get("response", "")
            intent = result.get("intent", "chat")

            if intent and intent != "chat":
                intent_display = {
                    "scan": "🔍 Tarama",
                    "action": "⚡ Eylem",
                    "exploit": "💥 Exploit",
                    "find_vulnerability": "🔎 Zafiyet Arama",
                    "needs_target": "🎯 Hedef Gerekli",
                }.get(intent, f"📋 {intent}")
                self.console.print(f"   [dim]{intent_display}[/dim]")

            if response:
                self.console.print(f"\n[DRAKBEN] {response}\n", style=self.COLORS["cyan"])

            if intent == "needs_target":
                return

            if self.config.target and intent == "action":
                self._show_orchestrator_actions(lang)
        else:
            error = result.get("error", "Unknown error")
            self.console.print(f"\n[red]Hata: {error}[/]\n")

    def _show_orchestrator_actions(self, lang: str) -> None:
        """Show suggested actions and ask user to run."""
        from rich.panel import Panel

        actions = self.orchestrator._get_phase_actions()
        if not actions:
            return

        self._display_actions_panel(actions, lang, Panel)
        self._handle_action_selection(actions, lang)

    def _display_actions_panel(self, actions: list, lang: str, Panel: type) -> None:
        """Display the actions panel."""
        title = "Suggested Actions" if lang == "en" else "Önerilen Eylemler"
        lines = []
        for i, action in enumerate(actions[:3], 1):
            tool = action.get("tool", "?")
            desc = action.get("description", "")
            cmd = action.get("command", "")
            lines.append(f"  {i}. [{tool}] {desc}")
            if cmd:
                lines.append(f"     > {cmd}")
        content = "\n".join(lines)
        self.console.print(Panel(content, title=title, border_style=self.STYLE_DIM_CYAN, padding=(0, 1)))

    def _handle_action_selection(self, actions: list, lang: str) -> None:
        """Handle user selection of actions."""
        if not actions:
            return
        first_cmd = actions[0].get("command", "")
        if not first_cmd:
            return

        prompt_msg = "Run? [y/n/2/3/s]" if lang == "en" else "Çalıştır? [e/h/2/3/s]"
        try:
            resp = Prompt.ask(prompt_msg, default="y" if lang == "en" else "e").lower().strip()
            self._execute_selected_action(resp, actions, lang)
        except KeyboardInterrupt:
            pass

    def _execute_selected_action(self, resp: str, actions: list, lang: str) -> None:
        """Execute the selected action based on user response."""
        if resp in {"y", "e"}:
            self._execute_with_orchestrator(actions[0].get("command", ""))
        elif resp == "2" and len(actions) > 1:
            self._execute_with_orchestrator(actions[1].get("command", ""))
        elif resp == "3" and len(actions) > 2:
            self._execute_with_orchestrator(actions[2].get("command", ""))
        elif resp == "s":
            skip_msg = "Skipped." if lang == "en" else "Atlandı."
            self.console.print(f"[dim]{skip_msg}[/]\n")

    def _execute_with_orchestrator(self, command: str) -> None:
        """Execute command through orchestrator (with LLM analysis)."""
        self.console.print(f"\n[{self.STYLE_BOLD_CYAN}]> {command}[/]\n")

        try:
            result = self.orchestrator.execute_tool(command, live_output=True, analyze=True)

            if result.get("success"):
                analysis = result.get("analysis", {})
                if analysis:
                    findings = analysis.get("findings", [])
                    next_action = analysis.get("next_action")

                    if findings:
                        self.console.print("\n[bold]Findings:[/]")
                        for f in findings[:5]:
                            self.console.print(f"  [+] {f}")

                    if next_action:
                        self.console.print(f"\n[dim]Suggested next: {next_action}[/]")

                self.orchestrator.advance_phase()
            else:
                error = result.get("error", "Command failed")
                self.console.print(f"\n[red][-] {error}[/]")

        except Exception as e:
            self.console.print(f"\n[red][-] Error: {e}[/]")

    # ── Brain fallback path ─────────────────────────────────────────

    def _process_with_brain_fallback(self, user_input: str, lang: str) -> None:
        """Fallback to old brain processing."""
        from core.ui.unified_display import ThinkingDisplay

        if not self.brain:
            from core.agent.brain import DrakbenBrain

            self.brain = DrakbenBrain()

        thinking_display = ThinkingDisplay(console=self.console, language=lang)

        try:
            phase = ""
            if self.orchestrator:
                phase = getattr(self.orchestrator, "current_phase", "")

            thinking_display.start_thinking(
                target=self.config.target or "",
                phase=phase,
                model=getattr(self.brain, "model_name", "") if self.brain else "",
            )

            if self.brain is None:
                msg = "self.brain must not be None"
                raise AssertionError(msg)

            thinking_display.update(sub_message=user_input[:50] + "..." if len(user_input) > 50 else user_input)

            result = self.brain.think(user_input, self.config.target, lang)

            llm_success = result.get("success", True) if isinstance(result, dict) else True
            if not llm_success:
                error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else "Error"
                thinking_display.finish_thinking(success=False)
                self.console.print(f"[red]LLM Error: {error_msg}[/]")
                return

            thinking_display.set_analyzing("response")
            thinking_display.finish_thinking(success=True)

            self._handle_ai_response_text(result, lang)

            steps = result.get("steps", [])
            if steps and isinstance(steps, list) and len(steps) > 0:
                self._execute_steps_with_approval(steps, lang)
            else:
                self._handle_ai_command(result, lang)

        except KeyboardInterrupt:
            self.console.print("\n🛑 İptal edildi.", style="yellow")

    # ── Step execution with approval ────────────────────────────────

    def _execute_steps_with_approval(self, steps: list, lang: str) -> None:
        """Execute plan steps with user approval for each step."""
        total = len(steps)

        for i, step in enumerate(steps, 1):
            result = self._process_single_step(step, i, total, lang)
            if result == "stop":
                return

        done_msg = "✅ Tüm adımlar tamamlandı." if lang == "tr" else "✅ All steps completed."
        self.console.print(f"\n{done_msg}\n", style="green")

    def _process_single_step(self, step: dict, index: int, total: int, lang: str) -> str:
        """Process a single step with approval.

        Returns:
            'stop' / 'skip' / 'done'
        """
        from core.ui.unified_display import ConfirmationRequest, RiskLevel, UnifiedConfirmation

        command = step.get("command") or step.get("tool", "")
        if not command:
            return "skip"

        risk_level = self._get_command_risk_level(command)

        description = step.get("description", "")
        step_header = f"[{index}/{total}] {description}" if description else f"[{index}/{total}]"
        self.console.print(f"\n⏳ {step_header}", style="cyan")

        confirmation = UnifiedConfirmation(console=self.console, language=lang)
        request = ConfirmationRequest(
            command=command,
            risk_level=risk_level,
            reason=description or (f"Step {index} of {total}"),
            details=[f"Tool: {step.get('tool', 'shell')}" if step.get("tool") else ""],
            allow_auto=risk_level == RiskLevel.LOW,
        )

        approved = confirmation.ask(request)

        if not approved:
            skip_msg = "⏭️ Adım atlandı." if lang == "tr" else "⏭️ Step skipped."
            self.console.print(skip_msg, style="dim")
            return "skip"

        self._execute_command(command)
        self._show_next_step_hint(index, total, step, lang)
        return "done"

    def _get_command_risk_level(self, command: str) -> Any:
        """Determine risk level for a command."""
        from core.ui.unified_display import RiskLevel

        command_lower = command.lower()

        critical_patterns = ["rm -rf", "mkfs", "dd if=", "> /dev/", "shutdown", "reboot"]
        if any(p in command_lower for p in critical_patterns):
            return RiskLevel.CRITICAL

        high_patterns = ["sudo", "exploit", "msfconsole", "reverse", "shell", "payload"]
        if any(p in command_lower for p in high_patterns):
            return RiskLevel.HIGH

        medium_patterns = ["nmap", "nikto", "sqlmap", "hydra", "gobuster", "curl", "wget"]
        if any(p in command_lower for p in medium_patterns):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _show_next_step_hint(self, current_idx: int, total: int, _steps: dict, lang: str) -> None:
        """Show hint about next step if available."""
        if current_idx >= total:
            return
        next_msg = "⏳ Sonraki adıma geçiliyor..." if lang == "tr" else "⏳ Moving to next step..."
        self.console.print(f"\n{next_msg}", style=self.STYLE_DIM_CYAN)

    def _ask_step_approval(self, lang: str) -> str:
        """Ask user for step approval.

        Returns: 'yes' / 'no' / 'stop'
        """
        prompt_text, choices, yes_set, stop_set = self._get_approval_config(lang)

        try:
            resp = Prompt.ask(prompt_text, choices=choices, default=choices[0])
            if resp in yes_set:
                return "yes"
            if resp in stop_set:
                return "stop"
            return "no"
        except KeyboardInterrupt:
            return "stop"

    def _get_approval_config(self, lang: str) -> tuple[str, list[str], set[str], set[str]]:
        """Get approval prompt configuration for language."""
        if lang == "tr":
            return (
                "Çalıştır? [e]vet/[h]ayır/[d]urdur",
                ["e", "h", "d"],
                {"e"},
                {"d"},
            )
        return (
            "Run? [y]es/[n]o/[s]top",
            ["y", "n", "s"],
            {"y"},
            {"s"},
        )

    # ── Target extraction ───────────────────────────────────────────

    def _extract_target_from_text(self, text: str) -> str | None:
        """Doğal dilden hedef (domain/IP) çıkar.

        Örnekler:
        - "filmfabrikasi.com sitesini tara" -> filmfabrikasi.com
        - "192.168.1.1 adresini kontrol et" -> 192.168.1.1
        - "https://example.com'u tara" -> example.com
        """
        # URL pattern (with protocol)
        url_match = re.search(
            r"https?://([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}",
            text,
        )
        if url_match:
            domain = url_match.group(0)
            domain = re.sub(r"^https?://", "", domain)
            domain = domain.split("/")[0]
            return domain

        # Domain pattern (without protocol)
        domain_match = re.search(
            r"\b([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}\b",
            text,
        )
        if domain_match:
            return domain_match.group(0)

        # IP address pattern
        ip_match = re.search(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            text,
        )
        if ip_match:
            return ip_match.group(0)

        return None

    # ── Response handling ───────────────────────────────────────────

    def _handle_ai_response_text(self, result: Any, lang: str) -> None:
        """Handle displaying the AI response text."""
        response_text = self._extract_response_text(result)

        if response_text:
            self.console.print(f"\n[DRAKBEN] {response_text}\n", style=self.COLORS["cyan"])
            self._show_planned_steps(result, lang)
        elif result.get("error"):
            self.console.print(f"\n❌ Hata: {result['error']}\n", style="red")
        else:
            self._show_offline_message(lang)

    def _extract_response_text(self, result: Any) -> str | None:
        """Extract response text from result dict."""
        return result.get("llm_response") or result.get("reply") or result.get("response") or result.get("reasoning")

    def _show_planned_steps(self, result: Any, lang: str) -> None:
        """Show planned steps from AI response."""
        from rich.panel import Panel

        steps = result.get("steps", [])
        if not steps or not isinstance(steps, list):
            return

        step_lines = []
        for i, s in enumerate(steps[:5]):
            action = s.get("action", s.get("tool", "unknown"))
            desc = s.get("description", s.get("tool", ""))[:50]
            step_lines.append(f"  {i + 1}. {action} - {desc}")

        step_text = "\n".join(step_lines)
        if step_text.strip():
            title = "Planlanan Adimlar" if lang == "tr" else "Planned Steps"
            self.console.print(
                Panel(step_text, title=title, border_style=self.STYLE_DIM_CYAN, padding=(0, 1)),
            )

    def _show_offline_message(self, lang: str) -> None:
        """Show offline/no connection message."""
        offline_msg = (
            "LLM bağlantısı yok. Lütfen API ayarlarını kontrol edin."
            if lang == "tr"
            else "No LLM connection. Please check API settings."
        )
        self.console.print(f"\n⚠️ {offline_msg}\n", style="yellow")

    # ── Single command handling ─────────────────────────────────────

    def _handle_ai_command(self, result: Any, lang: str) -> None:
        """Handle executing a single command suggested by AI (backward compat)."""
        command = result.get("command")
        if not command:
            return

        if command.strip().startswith("/"):
            self.console.print(f"🤖 Otomatik işlem: {command}", style="dim")
            self._execute_command(command)
            return

        from rich.panel import Panel

        self.console.print(
            Panel(
                f"💻 {command}",
                border_style="yellow",
                padding=(0, 1),
            ),
        )

        approval = self._ask_step_approval(lang)

        if approval == "yes":
            self._execute_command(command)
        elif approval == "stop":
            stop_msg = "⚠️ İşlem durduruldu." if lang == "tr" else "⚠️ Operation stopped."
            self.console.print(f"\n{stop_msg}\n", style="yellow")
        else:
            skip_msg = "⏭️ Komut atlandı." if lang == "tr" else "⏭️ Command skipped."
            self.console.print(skip_msg, style="dim")

    def _execute_command(self, command: str) -> None:
        """Execute command."""
        lang: str = self.config.language

        if command.strip().startswith("/"):
            self.console.print(
                f"🔄 Dahili komut çalıştırılıyor: {command}",
                style="dim",
            )
            self._handle_command(command)
            return

        self._ensure_agent_initialized()

        msg: str = "Çalıştırılıyor..." if lang == "tr" else "Executing..."
        self.console.print(f"⚡ {msg}", style=self.COLORS["yellow"])

        if self.agent is None:
            raise AssertionError(self.MSG_AGENT_NOT_NONE)
        if self.agent.executor is None:
            msg = "self.agent.executor must not be None"
            raise AssertionError(msg)
        result: ExecutionResult = self.agent.executor.terminal.execute(
            command,
            timeout=300,
        )

        self._display_execution_result(result, command)

    def _display_execution_result(self, result: ExecutionResult, command: str) -> None:
        """Display execution result and report to brain."""
        if result.status.value == "success":
            self.console.print(
                f"✅ OK ({result.duration:.1f}s)",
                style=self.COLORS["green"],
            )
            if result.stdout:
                self.console.print(result.stdout[:500], style="dim")
        else:
            self.console.print(f"❌ Hata: {result.stderr[:150]}", style="red")

        if self.brain:
            output_content: str = result.stdout if result.stdout else result.stderr
            parts = command.strip().split() if command else []
            tool_name: str = parts[0] if parts else "unknown"
            self.brain.observe(
                tool=tool_name,
                output=output_content,
                success=(result.status.value == "success"),
            )
