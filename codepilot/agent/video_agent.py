"""
Automated Demo Video Agent for CodePilot Multi-Agent Architecture.
Produces project showcase storyboard, narration script, visual frames,
and renders a real playable MP4 demonstration video using FFmpeg for hackathon judges.
"""
import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont

from codepilot.agent.base_agent import BaseSpecializedAgent, AgentTask, AgentResult
from codepilot.safety.policy import SafetyPolicy
from codepilot.llm.adapter import LLMAdapter


class DemoVideoAgent(BaseSpecializedAgent):
    agent_id: str = "demo_video"
    agent_role: str = "Automated Demo Video Agent"
    is_read_only: bool = True
    description: str = "Generates project showcase storyboard, narration, visual frames, and renders a playable MP4 demo video."

    def __init__(self, workspace_root: str, llm: LLMAdapter, safety: SafetyPolicy):
        super().__init__(workspace_root, llm, safety)
        self.workspace_path = Path(workspace_root).resolve()

    def _get_ffmpeg_path(self) -> Optional[str]:
        """Locates FFmpeg executable via imageio-ffmpeg or system PATH."""
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass

        sys_exe = shutil.which("ffmpeg")
        if sys_exe and os.path.exists(sys_exe):
            return sys_exe
        return None

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        errors: List[str] = []

        demo_dir = self.workspace_path / "artifacts" / "demo"
        screenshots_dir = demo_dir / "screenshots"
        demo_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg_exe = self._get_ffmpeg_path()
        if not ffmpeg_exe:
            err_msg = "FFmpeg executable not found. Cannot render playable MP4 video. Install imageio-ffmpeg or ffmpeg."
            errors.append(err_msg)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="FAILED",
                findings=[],
                artifacts={},
                evidence={"ffmpeg_available": False},
                metrics={"runtime_seconds": round(time.time() - start_time, 2)},
                errors=errors,
                summary=err_msg
            )

        # 1. Read repository context and architecture documentation
        repo_summary = self._gather_project_context()

        # 2. Generate Storyboard and Narration
        slides_data = self._generate_storyboard_content(repo_summary)

        storyboard_path = demo_dir / "storyboard.md"
        narration_path = demo_dir / "narration.md"

        storyboard_path.write_text(self._render_storyboard_markdown(slides_data), encoding="utf-8")
        narration_path.write_text(self._render_narration_markdown(slides_data), encoding="utf-8")

        # 3. Render Visual Presentation Frames / Slides (PNG)
        image_files = self._render_slide_images(slides_data, screenshots_dir)

        # 4. Synthesize Audio Narration (macOS 'say' command if available)
        audio_file = self._synthesize_audio(slides_data, demo_dir)

        # 5. Compile Real Playable MP4 Video using FFmpeg
        output_mp4 = demo_dir / "demo.mp4"
        video_success = self._compile_video(ffmpeg_exe, screenshots_dir, image_files, audio_file, output_mp4)

        if not video_success or not output_mp4.exists() or output_mp4.stat().st_size == 0:
            err = "Video compilation failed or produced empty MP4."
            errors.append(err)
            status = "PARTIAL"
        else:
            status = "SUCCESS"

        runtime = round(time.time() - start_time, 2)
        summary = (
            f"Demo Video Agent generated presentation materials in artifacts/demo/: "
            f"storyboard.md, narration.md, {len(image_files)} slides, and playable video demo.mp4 ({output_mp4.stat().st_size if output_mp4.exists() else 0} bytes)."
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=status,
            findings=[{
                "slides_count": len(slides_data),
                "video_rendered": output_mp4.exists() and output_mp4.stat().st_size > 0,
                "video_path": str(output_mp4),
                "file_size_bytes": output_mp4.stat().st_size if output_mp4.exists() else 0
            }],
            artifacts={
                "storyboard_md": str(storyboard_path),
                "narration_md": str(narration_path),
                "screenshots_dir": str(screenshots_dir),
                "demo_mp4": str(output_mp4)
            },
            evidence={
                "slides_rendered": len(image_files),
                "ffmpeg_binary": ffmpeg_exe,
                "playable_mp4_bytes": output_mp4.stat().st_size if output_mp4.exists() else 0
            },
            metrics={"runtime_seconds": runtime, "slides_count": len(slides_data)},
            errors=errors,
            summary=summary
        )

    def _gather_project_context(self) -> Dict[str, Any]:
        arch_path = self.workspace_path / "artifacts" / "architecture" / "architecture.md"
        arch_text = arch_path.read_text(encoding="utf-8") if arch_path.exists() else ""

        readme_path = self.workspace_path / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

        return {
            "name": "CodePilot Autonomous Coding Harness",
            "arch": arch_text[:2000],
            "readme": readme_text[:2000]
        }

    def _generate_storyboard_content(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "scene": 1,
                "title": "CodePilot: Autonomous Software Engineering Harness",
                "subtitle": "LLM-First Multi-Agent Architecture for Real-World Development",
                "bullets": [
                    "Problem: Fragile AI coders relying on rigid keyword routing & mock responses",
                    "Solution: Unified multi-agent coordination with real foundation LLM / on-device SLM",
                    "Experience: Claude Code & Antigravity-style autonomous pairing"
                ],
                "narration": "Welcome to CodePilot, an autonomous software engineering system designed for real-world development without mock intelligence. Unlike brittle keyword-based tools, CodePilot unifies real foundation models with specialized agent swarms."
            },
            {
                "scene": 2,
                "title": "Central Multi-Agent Orchestrator",
                "subtitle": "Dependency-Aware Scheduling & Context Budgeting",
                "bullets": [
                    "Understands arbitrary natural language queries without keyword filters",
                    "Answers general questions directly with zero tool overhead",
                    "Coordinates independent read-only agents concurrently in parallel",
                    "Serializes and controls code modification workflows safely"
                ],
                "narration": "At the core sits the Central Orchestrator. When a user asks a general conceptual question, the orchestrator responds directly. When faced with complex engineering goals, it plans task dependencies and coordinates specialized agents."
            },
            {
                "scene": 3,
                "title": "Specialized Agent Swarm",
                "subtitle": "Domain-Specific Intelligence Grounded in Real Repositories",
                "bullets": [
                    "Security Auditor: AST-based secret scanning, injection detection, and remediation",
                    "Code Quality Agent: Duplication detection & simplification without added bloat",
                    "Architecture Agent: Automated dependency graphs, execution flow, & Mermaid diagrams",
                    "Demo Video Agent: Automated showcase generation with playable MP4 rendering"
                ],
                "narration": "CodePilot features four specialized autonomous agents. The Security Auditor inspects code for vulnerabilities. The Code Quality Agent eliminates duplicate blocks. The Architecture Agent produces verified technical diagrams. And the Video Agent generates real demonstration videos."
            },
            {
                "scene": 4,
                "title": "Controlled Tools & Safety Sandbox",
                "subtitle": "Path Containment, Command Whitelisting, & Git Tracing",
                "bullets": [
                    "Strict workspace confinement prevents unauthorized path escapes",
                    "Dangerous shell commands blocked by safety policy",
                    "Complete telemetry metrics: token tracking, runtime, & git diffs",
                    "Full reproducibility across every autonomous execution turn"
                ],
                "narration": "Safety is paramount. All tool invocations are guarded by strict containment policies, preventing path traversal or hazardous system commands, while telemetry logs every prompt token and execution milestone."
            },
            {
                "scene": 5,
                "title": "Dynamic Failure Recovery & Verification",
                "subtitle": "Independent Test Verification & Automated Re-Planning",
                "bullets": [
                    "Automated test suite execution validates all code modifications",
                    "FailureClassifier categorizes syntax errors, assertion failures, and timeouts",
                    "RecoveryStrategy generates targeted repair plans dynamically",
                    "EvidenceReporter produces structured verification audit records"
                ],
                "narration": "When a fix fails, CodePilot doesn't give up. The Failure Classifier diagnoses the root cause, dynamically refactors the plan, and verifies all assertions before reporting success."
            },
            {
                "scene": 6,
                "title": "Hackathon Ready & Extensible",
                "subtitle": "Local SLM Support & Comprehensive Model Provider Ecosystem",
                "bullets": [
                    "Supports on-device Apple Silicon SLMs via Ollama (100% offline & private)",
                    "Native support for Groq, Gemini, OpenAI, and Anthropic models",
                    "Real observable UI across Interactive CLI and Web Dashboard",
                    "True LLM-first autonomy for next-generation software development"
                ],
                "narration": "CodePilot operates locally on-device using private SLMs or connects to major cloud frontier models. This is true autonomous engineering built for the future."
            }
        ]

    def _render_storyboard_markdown(self, slides: List[Dict[str, Any]]) -> str:
        lines = [
            "# 🎬 CodePilot Project Showcase Storyboard",
            "This storyboard defines the scenes, visual layout, and sequence for the automated demo video.\n",
            "---"
        ]
        for s in slides:
            lines.append(f"## Scene {s['scene']}: {s['title']}")
            lines.append(f"**Subtitle**: {s['subtitle']}\n")
            lines.append("**Visual Elements**:")
            for b in s["bullets"]:
                lines.append(f"- {b}")
            lines.append(f"\n**Narration Script**:\n> *\"{s['narration']}\"*\n")
            lines.append("---\n")
        return "\n".join(lines)

    def _render_narration_markdown(self, slides: List[Dict[str, Any]]) -> str:
        lines = [
            "# 🎙️ CodePilot Demonstration Narration Script",
            "Audio script aligned with each visual scene of the demo video.\n",
            "---"
        ]
        for s in slides:
            lines.append(f"### [Scene {s['scene']} — {s['title']}]")
            lines.append(f"{s['narration']}\n")
        return "\n".join(lines)

    def _render_slide_images(self, slides: List[Dict[str, Any]], output_dir: Path) -> List[Path]:
        width, height = 1280, 720
        image_files = []

        for idx, s in enumerate(slides, 1):
            img = Image.new("RGB", (width, height), color=(15, 23, 42))  # Deep slate background
            draw = ImageDraw.Draw(img)

            # Gradient Header Bar
            draw.rectangle([(0, 0), (width, 8)], fill=(56, 189, 248))  # Cyan highlight

            # Decorative badge
            badge_text = f"SCENE {s['scene']:02d} // CODEPILOT HARNESS"
            draw.text((60, 40), badge_text, fill=(56, 189, 248))

            # Main Title
            draw.text((60, 75), s["title"], fill=(248, 250, 252))

            # Subtitle
            draw.text((60, 120), s["subtitle"], fill=(148, 163, 184))

            # Horizontal Separator
            draw.line([(60, 160), (width - 60, 160)], fill=(51, 65, 85), width=2)

            # Content Cards / Bullet Points
            y_pos = 190
            for bullet in s["bullets"]:
                # Card background
                draw.rectangle([(60, y_pos), (width - 60, y_pos + 65)], fill=(30, 41, 59), outline=(71, 85, 105), width=1)
                # Accent indicator
                draw.rectangle([(60, y_pos), (66, y_pos + 65)], fill=(52, 211, 153))  # Emerald accent
                # Bullet text
                draw.text((85, y_pos + 22), f"•  {bullet}", fill=(241, 245, 249))
                y_pos += 80

            # Narration Box at Bottom
            narration_box_y = height - 120
            draw.rectangle([(60, narration_box_y), (width - 60, height - 30)], fill=(15, 23, 42), outline=(56, 189, 248), width=1)
            draw.text((80, narration_box_y + 12), "🎙️ NARRATION AUDIO:", fill=(56, 189, 248))
            draw.text((80, narration_box_y + 38), f'"{s["narration"][:110]}..."', fill=(203, 213, 225))

            # Save slide
            slide_path = output_dir / f"slide_{idx:02d}.png"
            img.save(slide_path, "PNG")
            image_files.append(slide_path)

        return image_files

    def _synthesize_audio(self, slides: List[Dict[str, Any]], demo_dir: Path) -> Optional[Path]:
        """Synthesizes narration audio using macOS native 'say' command if available."""
        if sys.platform != "darwin" or not os.path.exists("/usr/bin/say"):
            return None

        combined_text = " ... ".join([s["narration"] for s in slides])
        aiff_path = demo_dir / "narration.aiff"
        wav_path = demo_dir / "narration.wav"

        try:
            # Generate AIFF speech via macOS native TTS engine
            res = subprocess.run(["/usr/bin/say", "-o", str(aiff_path), combined_text], timeout=25, capture_output=True)
            if res.returncode == 0 and aiff_path.exists():
                return aiff_path
        except Exception:
            pass
        return None

    def _compile_video(self, ffmpeg_exe: str, screenshots_dir: Path, image_files: List[Path], audio_file: Optional[Path], output_mp4: Path) -> bool:
        """Assembles slide PNGs into a playable MP4 video using FFmpeg."""
        try:
            if output_mp4.exists():
                output_mp4.unlink()

            concat_file = screenshots_dir / "slides_input.txt"
            duration_per_slide = 4.0  # 4 seconds per slide
            with open(concat_file, "w", encoding="utf-8") as f:
                for img_p in image_files:
                    f.write(f"file '{img_p.resolve()}'\n")
                    f.write(f"duration {duration_per_slide}\n")
                if image_files:
                    f.write(f"file '{image_files[-1].resolve()}'\n")

            cmd = [
                ffmpeg_exe,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file.resolve())
            ]

            if audio_file and audio_file.exists():
                cmd.extend(["-i", str(audio_file.resolve())])

            cmd.extend([
                "-c:v", "libx264",
                "-r", "25",
                "-pix_fmt", "yuv420p"
            ])

            if audio_file and audio_file.exists():
                cmd.extend([
                    "-c:a", "aac",
                    "-shortest"
                ])

            cmd.append(str(output_mp4.resolve()))

            res = subprocess.run(cmd, cwd=str(self.workspace_path), timeout=60, capture_output=True)
            return res.returncode == 0 and output_mp4.exists() and output_mp4.stat().st_size > 0
        except Exception:
            return False
