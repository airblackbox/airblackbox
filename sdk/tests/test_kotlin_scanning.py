"""Kotlin support in the compliance scanners.

Kotlin shares Java's library adapters (same JVM ecosystem) and adds its own
syntax: top-level functions, expression bodies, KDoc, string templates,
runCatching, kotlin-logging, Koog and openai-kotlin.
"""

import re

import pytest

from air_blackbox.compliance.code_scanner import (
    _find_source_files,
    _kotlin_definitions,
    scan_codebase,
)
from air_blackbox.compliance.engine import run_all_checks
from air_blackbox.compliance.sources import Source, language_of
from air_blackbox.gateway_client import GatewayStatus


def _write(root, files):
    for name, code in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)


def _by_name(findings):
    return {f.name: (f.status, f.evidence) for f in findings}


@pytest.mark.parametrize("name, lang", [
    ("Agent.kt", "kotlin"), ("script.main.kts", "kotlin"),
    ("build.gradle.kts", None), ("settings.gradle.kts", None),
])
def test_language_of(name, lang):
    assert language_of(name) == lang


def test_kotlin_build_output_and_tests(tmp_path):
    _write(tmp_path, {
        "src/main/kotlin/Agent.kt": "/** Agent. */\nclass Agent {\n    /** Run. */\n    fun run(): String = \"\"\n}\n",
        "src/test/kotlin/AgentTest.kt": "class AgentTest { fun t() {} }\n",
        "build/generated/G.kt": "class G\n",
        ".kotlin/sessions/x.kt": "class X\n",
    })
    files = {f.split(str(tmp_path) + "/", 1)[1] for f in _find_source_files(str(tmp_path))}
    assert files == {"src/main/kotlin/Agent.kt", "src/test/kotlin/AgentTest.kt"}
    docs = _by_name(scan_codebase(str(tmp_path)))["Code documentation (docstrings)"]
    assert docs[0] == "pass" and docs[1].startswith("2/2 ") and "KDoc" in docs[1]


KT = '''/** Service. */
@Service
class Svc(private val repo: Repo) : Base() {
    constructor() : this(Repo())
    /** Renders it. */
    override fun toString(): String = "x"
    @Transactional
    fun list() = repo.findAll()
    private fun helper() {}
    abstract fun size(): Int
    suspend fun ask(
        q: String,
        n: Int,
    ): String {
        return q
    }
    fun <T> generic(c: Class<T>): T? = null
    fun String.shout() = uppercase()
    fun run() {
        val x = listOf(1).map { it + 1 }
        foo(fun() {})
    }
    companion object {
        fun create() = Svc(Repo())
    }
}
interface Api { fun get(id: String): String }
fun interface Handler { fun handle(x: Int) }
data class Point(val x: Int, val y: Int)
object Registry
fun topLevel(x: Int) = x
'''


def test_kotlin_definitions():
    defs = {d.name: d for d in _kotlin_definitions(Source(KT, "kotlin"))}
    assert set(defs) == {"Svc", "toString", "list", "helper", "ask", "generic", "shout", "run",
                         "create", "Api", "Handler", "Point", "Registry", "topLevel"}
    assert defs["Svc"].kind == "class" and defs["Svc"].documented   # annotation in between
    assert defs["toString"].documented and defs["toString"].typed
    assert not defs["list"].documented                              # doc belongs to toString
    assert defs["helper"].private
    assert defs["ask"].typed and defs["topLevel"].typed
    # no parameters and an inferred return type: as untyped as `def run():`
    assert not defs["run"].typed and not defs["list"].typed
    assert "size" not in defs and "get" not in defs                 # declarations without bodies


def test_kotlin_idioms(tmp_path):
    _write(tmp_path, {"Agent.kt": '''import io.github.oshai.kotlinlogging.KotlinLogging
import dev.langchain4j.model.chat.ChatModel

private val logger = KotlinLogging.logger {}

class Agent(private val model: ChatModel, private val requireApproval: Boolean) {
    fun ask(userInput: String): String = runCatching {
        model.chat("Answer: $userInput")
    }.getOrElse {
        logger.error(it) { "failed" }
        ""
    }
}
'''})
    got = _by_name(scan_codebase(str(tmp_path)))
    assert got["LLM call error handling"][0] == "pass"
    assert got["Application logging"][0] == "pass"
    assert got["Human-in-the-loop patterns"][0] == "pass"      # requireApproval
    assert got["Unsafe input handling"][0] == "warn"           # "$userInput" in a prompt
    assert got["Type annotations"][0] == "pass"


def test_println_is_not_logging(tmp_path):
    _write(tmp_path, {"A.kt": "fun main() { println(1) }\n"})
    status, evidence = _by_name(scan_codebase(str(tmp_path)))["Application logging"]
    assert status == "fail" and "SLF4J" in evidence


def test_kotlin_frameworks_and_advice(tmp_path):
    _write(tmp_path, {"A.kt": "import ai.koog.agents.core.agent.AIAgent\n"
                              "import com.aallam.openai.client.OpenAI\n"
                              "import org.springframework.ai.chat.client.ChatClient\n"})
    results, frameworks, _rec, _ = run_all_checks(GatewayStatus(), str(tmp_path), "all")
    assert frameworks == ["Koog", "OpenAI Kotlin (aallam)", "Spring AI"]
    hints = [c.get("fix_hint", "") for a in results for c in a["checks"]]
    assert not any(re.search(r"pip install air-[\w-]+-trust", h) for h in hints)


def test_kotlin_inherits_java_library_patterns(tmp_path):
    _write(tmp_path, {"A.kt": "import io.github.bucket4j.Bucket\n"
                              "val bucket: Bucket = Bucket.builder().build()\n"})
    assert _by_name(scan_codebase(str(tmp_path)))["Usage limits / budget controls"][0] == "pass"
