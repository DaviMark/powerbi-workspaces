"""End-to-end tests for the Power BI Workspaces CLI. Standard library only.

    python -m unittest discover -s _sistema/testes -v
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "_sistema"))

from workspaces import cli, pbit, prototipo, secrets, tmdl  # noqa: E402
from workspaces.sqlsync import select_aliases  # noqa: E402
from workspaces.util import m_string, pascal, slugify  # noqa: E402


def make_pbit(path: Path) -> None:
    """A tiny but realistic .pbit: legacy layout + model with classic anti-patterns."""
    model = {
        "name": "Legacy",
        "compatibilityLevel": 1550,
        "model": {
            "culture": "pt-BR",
            "tables": [
                {
                    "name": "Vendas",
                    "columns": [
                        {"name": "id_cliente", "dataType": "int64", "sourceColumn": "id_cliente"},
                        {"name": "Data", "dataType": "dateTime", "sourceColumn": "Data"},
                        {"name": "Valor", "dataType": "double", "sourceColumn": "Valor"},
                        {"name": "Observacao", "dataType": "string", "sourceColumn": "Observacao"},
                        {"name": "Margem", "dataType": "double", "type": "calculated",
                         "expression": "Vendas[Valor] * 0.2"},
                    ],
                    "partitions": [{"name": "Vendas", "mode": "import", "source": {"type": "m", "expression": [
                        "let",
                        '    Fonte = Sql.Database("10.0.0.15", "ERP"),',
                        '    Tab = Fonte{[Schema="dbo",Item="vendas"]}[Data],',
                        '    Tipos = Table.TransformColumnTypes(Tab,{{"Valor", type number}}),',
                        '    Filtro = Table.SelectRows(Tipos, each [Valor] > 0)',
                        "in",
                        "    Filtro"]}}],
                    "measures": [{"name": "Total Vendas", "expression": "SUM(Vendas[Valor])"}],
                },
                {
                    "name": "Clientes",
                    "columns": [
                        {"name": "id_cliente", "dataType": "int64", "sourceColumn": "id_cliente"},
                        {"name": "Nome", "dataType": "string", "sourceColumn": "Nome"},
                        {"name": "Telefone", "dataType": "string", "sourceColumn": "Telefone"},
                    ],
                    "partitions": [{"name": "Clientes", "mode": "import", "source": {
                        "type": "m", "expression": 'let Fonte = Sql.Database("10.0.0.15", "ERP") in Fonte'}}],
                },
                {"name": "LocalDateTable_123", "isHidden": True, "columns": [], "partitions": []},
            ],
            "relationships": [
                {"name": "r1", "fromTable": "Vendas", "fromColumn": "id_cliente", "toTable": "Clientes",
                 "toColumn": "id_cliente", "crossFilteringBehavior": "bothDirections"},
            ],
        },
    }
    visual_cfg = {"singleVisual": {"visualType": "clusteredBarChart", "prototypeQuery": {"Select": [
        {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "Nome"}, "Name": "Clientes.Nome"},
        {"Measure": {"Expression": {"SourceRef": {"Source": "v"}}, "Property": "Total Vendas"},
         "Name": "Vendas.Total Vendas"}]},
        "projections": {"Category": [{"queryRef": "Clientes.Nome"}], "Y": [{"queryRef": "Vendas.Total Vendas"}]}}}
    layout = {"sections": [{"name": "s1", "displayName": "Resumo", "ordinal": 0, "width": 1280, "height": 720,
                            "visualContainers": [{"x": 0, "y": 0, "width": 400, "height": 300,
                                                  "config": json.dumps(visual_cfg)}]}]}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("DataModelSchema", json.dumps(model).encode("utf-16-le"))
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))
        z.writestr("Version", "1.28".encode("utf-16-le"))


class Sandbox(unittest.TestCase):
    """Copies the repo skeleton (no dashboards) to a temp folder."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pbw-test-"))
        for item in ("_sistema", "conexoes", "identidade-visual", "refatorar"):
            shutil.copytree(REPO / item, self.tmp / item, ignore=shutil.ignore_patterns("__pycache__", "testes"))
        shutil.copy(REPO / "workspaces.toml", self.tmp / "workspaces.toml")
        (self.tmp / "dashboards").mkdir()
        (self.tmp / "dashboards" / "LEIA-ME.md").write_text("# dashboards\n", encoding="utf-8")
        self._cwd = Path.cwd()
        import os
        os.chdir(self.tmp)

    def tearDown(self) -> None:
        import os
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args: str) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            code = cli.main(list(args))
        return code, buf.getvalue()


class TestHelpers(unittest.TestCase):
    def test_slug_and_pascal(self) -> None:
        self.assertEqual(slugify("Contas a Receber"), "contas-a-receber")
        self.assertEqual(slugify("  Gestão  de Frota / 2026 "), "gestao-de-frota-2026")
        self.assertEqual(pascal("Aging de Títulos"), "AgingDeTitulos")

    def test_m_string_escapes(self) -> None:
        self.assertEqual(m_string('SELECT "a"\nFROM t'), '"SELECT ""a""#(lf)FROM t"')
        self.assertEqual(m_string("x #(lf) y"), '"x #(#)(lf) y"')

    def test_select_aliases(self) -> None:
        sql = "SELECT a.id AS id, CAST(x AS date) AS [Data], SUM(v) total FROM t GROUP BY a.id"
        self.assertEqual(select_aliases(sql), ["id", "Data", "total"])
        self.assertIsNone(select_aliases("SELECT * FROM t"))


class TestNewDashboard(Sandbox):
    def test_new_validate_and_sync(self) -> None:
        code, out = self.run_cli("novo", "Acme/Comercial/Vendas/Painel de Vendas")
        self.assertEqual(code, 0, out)
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel-de-vendas"
        self.assertTrue((dash / "2-power-bi/PainelDeVendas.pbip").exists())   # ready to open
        self.assertEqual(sorted(p.name for p in dash.iterdir()),
                         ["1-seu-pedido", "2-power-bi", "3-entrega", "LEIA-ME.md", "trabalho-da-ia"])
        for f in ("1-seu-pedido/PEDIDO.md", "1-seu-pedido/anexos/consultas-sql",
                  "1-seu-pedido/anexos/imagens-e-rascunhos", "1-seu-pedido/anexos/documentos", "trabalho-da-ia/ficha.toml",
                  "trabalho-da-ia/desenho.md", "trabalho-da-ia/conferencia.md", "trabalho-da-ia/sql/LEIA-ME.md"):
            self.assertTrue((dash / f).exists(), f)
        pedido = (dash / "1-seu-pedido/PEDIDO.md").read_text(encoding="utf-8")
        self.assertIn("Regras de negócio", pedido)
        self.assertIn("Visuais que eu quero", pedido)
        pages = [json.loads(p.read_text(encoding="utf-8"))["displayName"]
                 for p in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json")]
        self.assertEqual(sorted(pages), ["Documentação", "Visão Geral"])  # prototype + documentation
        # add a SQL file and sync -> stub table is created with parameters (not hardcoded host)
        (dash / "trabalho-da-ia/sql/Fato Vendas.sql").write_text(
            "-- @description: vendas\nSELECT id AS id, valor AS [Valor] FROM bi.vendas", encoding="utf-8")
        code, out = self.run_cli("sincronizar-sql", "painel-de-vendas")     # by name
        self.assertEqual(code, 0, out)
        t = (dash / "2-power-bi/PainelDeVendas.SemanticModel/definition/tables/Fato Vendas.tmdl").read_text(encoding="utf-8")
        self.assertIn("Sql.Database(Erp_Server, Erp_Database)", t)
        self.assertIn("EnableFolding = true", t)
        # stub without columns must fail validation (PBW023)
        code, out = self.run_cli("validar", str(dash))
        self.assertEqual(code, 1)
        self.assertIn("PBW023", out)

    def test_english_aliases_still_work(self) -> None:
        code, out = self.run_cli("new", "Acme/Comercial/Vendas/Painel")
        self.assertEqual(code, 0, out)
        code, out = self.run_cli("open", "painel", "--so-caminho")
        self.assertEqual(code, 0, out)
        self.assertIn("Painel.pbip", out)

    def test_connect_switches_profile(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "trabalho-da-ia/sql/Fato.sql").write_text("SELECT 1 AS x FROM y", encoding="utf-8")
        code, out = self.run_cli("conectar", str(dash), "-c", "bigquery.example")
        self.assertEqual(code, 0, out)
        exprs = (dash / "2-power-bi/Painel.SemanticModel/definition/expressions.tmdl").read_text(encoding="utf-8")
        self.assertIn("Gcp_BillingProject", exprs)
        self.assertNotIn("Erp_Server", exprs)
        t = (dash / "2-power-bi/Painel.SemanticModel/definition/tables/Fato.tmdl").read_text(encoding="utf-8")
        self.assertIn("GoogleBigQuery.Database", t)

    def test_rejects_wrong_depth(self) -> None:
        code, out = self.run_cli("novo", "Acme/Vendas/Painel")
        self.assertEqual(code, 1)
        self.assertIn("4 níveis", out)


class TestPrototype(Sandbox):
    DESIGN = """# Desenho
## 3. Páginas
### Visão Geral
**Pergunta:** quanto vendemos?
| Zona | Visual | Campos |
|---|---|---|
| KPIs | Cartão | [Atualizado em] |
| KPIs | Cartão | [Vendas] |
| Tendência | Colunas | Calendario[Ano-Mês] × [Vendas] |
| Filtro | Segmentação | Dim Loja[Regional] |
| Detalhe | Tabela | Pedidos |
### Clientes
| Zona | Visual | Campos |
|---|---|---|
| Explicação | Barras | Cliente × [Vendas] |
### Documentação (obrigatória)
gerada
## 4. Decisões
"""

    def _pages(self, dash: Path) -> dict[str, list[dict]]:
        out = {}
        for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json"):
            name = json.loads(pj.read_text(encoding="utf-8"))["displayName"]
            out[name] = [json.loads(v.read_text(encoding="utf-8")) for v in pj.parent.glob("visuals/*/visual.json")]
        return out

    def test_parse_design(self) -> None:
        pages = prototipo.parse_design(self.DESIGN)
        self.assertEqual([p.name for p in pages], ["Visão Geral", "Clientes"])     # doc page skipped
        self.assertEqual(pages[0].question, "quanto vendemos?")
        self.assertEqual([i.zone for i in pages[0].items], ["kpis", "kpis", "main", "filters", "detail"])

    def test_prototype_pages_open_and_are_replaceable(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "trabalho-da-ia/desenho.md").write_text(self.DESIGN, encoding="utf-8")
        code, out = self.run_cli("prototipo", "painel")
        self.assertEqual(code, 0, out)
        pages = self._pages(dash)
        self.assertEqual(set(pages), {"Visão Geral", "Clientes", "Documentação"})
        types = [v["visual"]["visualType"] for v in pages["Visão Geral"]]
        self.assertIn("card", types)                     # [Atualizado em] exists in the model -> real card
        for vis in pages["Visão Geral"]:                 # everything inside the 1280x720 canvas
            pos = vis["position"]
            self.assertLessEqual(pos["x"] + pos["width"], 1280)
            self.assertLessEqual(pos["y"] + pos["height"], 720)
        order = json.loads(next(dash.glob("2-power-bi/*.Report/definition/pages/pages.json")).read_text(encoding="utf-8"))
        names = {pj.parent.name: json.loads(pj.read_text(encoding="utf-8"))["displayName"]
                 for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json")}
        self.assertEqual([names[p] for p in order["pageOrder"]], ["Visão Geral", "Clientes", "Documentação"])
        # a page rebuilt for real (no PROTÓTIPO marker) is kept on the next run
        clientes = next(pj.parent for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json")
                        if names[pj.parent.name] == "Clientes")
        for v in clientes.glob("visuals/*/visual.json"):
            v.write_text(v.read_text(encoding="utf-8").replace("PROTÓTIPO", "REAL"), encoding="utf-8")
        code, out = self.run_cli("prototipo", "painel")
        self.assertIn("mantida", out)
        self.assertTrue(clientes.exists())
        code, out = self.run_cli("validar", "painel")
        self.assertIn("PBW024", out)                     # prototype pages reported
        self.assertNotIn("PBW007", out)

    def test_broken_pbip_is_an_error(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "2-power-bi/Painel.pbip").write_text('{"artifacts": [{"report": {"path": "Outro.Report"}}]}', encoding="utf-8")
        code, out = self.run_cli("validar", "painel")
        self.assertEqual(code, 1)
        self.assertIn("PBW007", out)
        (dash / "2-power-bi/Painel.pbip").unlink()
        code, out = self.run_cli("validar", "painel")
        self.assertIn("exatamente 1 .pbip", out)

    def test_stray_file_points_to_anexos(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "meu-print.png").write_bytes(b"x")
        code, out = self.run_cli("validar", "painel")
        self.assertEqual(code, 1)
        self.assertIn("1-seu-pedido/anexos", out)


class TestTemplateDashboard(Sandbox):
    def test_copy_rename_and_adopt(self) -> None:
        self.run_cli("novo", "Nome da Empresa/Nome da Area/Nome da Subarea/Nome do Dashboard")
        tpl = self.tmp / "dashboards/nome-da-empresa"
        code, out = self.run_cli("validar")
        self.assertEqual(code, 0, out)                                   # the template is never validated
        self.assertNotIn("Nome do Dashboard", (self.tmp / "dashboards/CATALOGO.md").read_text(encoding="utf-8"))
        # the analyst duplicates and renames the folders, then fills the request
        dest = self.tmp / "dashboards/acme/comercial/vendas/painel-de-vendas"
        shutil.copytree(tpl / "nome-da-area/nome-da-subarea/nome-do-dashboard", dest)
        pedido = dest / "1-seu-pedido/PEDIDO.md"
        pedido.write_text(pedido.read_text(encoding="utf-8") + "\nMINHA REGRA\n", encoding="utf-8")
        (dest / "1-seu-pedido/anexos/consultas-sql/vendas.sql").write_text("SELECT 1", encoding="utf-8")
        code, out = self.run_cli("validar", str(dest))
        self.assertEqual(code, 1)
        self.assertIn("copiada do modelo", out)
        code, out = self.run_cli("novo", "Acme/Comercial/Vendas/Painel de Vendas")
        self.assertEqual(code, 0, out)
        text = pedido.read_text(encoding="utf-8")
        self.assertIn("MINHA REGRA", text)                                # the request is kept
        self.assertIn("# Pedido — Painel de Vendas", text)
        self.assertTrue((dest / "1-seu-pedido/anexos/consultas-sql/vendas.sql").exists())
        self.assertTrue((dest / "2-power-bi/PainelDeVendas.pbip").exists())
        self.assertFalse((dest / "2-power-bi/NomeDoDashboard.pbip").exists())
        code, out = self.run_cli("validar", str(dest))
        self.assertEqual(code, 0, out)

class TestWelcome(Sandbox):
    def ask(self) -> str:
        code, out = self.run_cli("boas-vindas", "--verificar")
        self.assertEqual(code, 0, out)
        return out.split()[0]

    def test_tour_is_offered_until_more_than_one_own_dashboard(self) -> None:
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # raw repository
        self.run_cli("novo", "Nome da Empresa/Nome da Area/Nome da Subarea/Nome do Dashboard")
        self.run_cli("novo", "Acme/Exemplo/Exemplo/Exemplo")
        ficha = self.tmp / "dashboards/acme/exemplo/exemplo/exemplo/trabalho-da-ia/ficha.toml"
        ficha.write_text(ficha.read_text(encoding="utf-8").replace('origin = "new"', 'example = true\norigin = "new"'),
                         encoding="utf-8")
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # template + example do not count
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel A")
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # 1 dashboard: still asks
        ph = self.tmp / "refatorar/nome-da-empresa/nome-da-area/nome-da-subarea/nome-do-dashboard"
        make_pbit(ph / "x.pbit")
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # pbit in a template folder
        legacy = self.tmp / "refatorar/acme/financeiro/cobranca/aging"
        legacy.mkdir(parents=True)
        make_pbit(legacy / "Aging.pbit")
        self.assertEqual(self.ask(), "NAO-PERGUNTAR")                               # 1 dashboard + 1 legacy
        code, out = self.run_cli("boas-vindas", "--hook")
        self.assertIn('"hookEventName": "SessionStart"', out)

class TestVisualStandard(Sandbox):
    def test_app_shell_and_company_theme(self) -> None:
        from workspaces import shell
        from workspaces.util import stable_id
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        rep = next(dash.glob("2-power-bi/*.Report"))
        for pj in rep.glob("definition/pages/*/page.json"):
            pid = pj.parent.name
            shell_ids = {stable_id(pid, k) for k in shell._keys()}
            names = {v.parent.name for v in pj.parent.glob("visuals/*/visual.json")}
            self.assertIn(stable_id(pid, "shell-sidebar"), names)             # sidebar on every page
            for vj in pj.parent.glob("visuals/*/visual.json"):
                if vj.parent.name in shell_ids:
                    continue
                x = json.loads(vj.read_text(encoding="utf-8"))["position"]["x"]
                self.assertGreaterEqual(x, shell.SIDEBAR_W)                    # content right of the sidebar
        report = json.loads((rep / "definition/report.json").read_text(encoding="utf-8"))
        self.assertNotIn("baseTheme", report["themeCollection"])              # no Microsoft base theme
        self.assertFalse((rep / "StaticResources/SharedResources").exists())
        theme = json.loads((rep / "StaticResources/RegisteredResources/acme-theme.json").read_text(encoding="utf-8"))
        self.assertFalse(theme["visualStyles"]["*"]["*"]["valueAxis"][0]["gridlineShow"])

class TestIdentity(Sandbox):
    def test_company_identity_applies_to_all_its_dashboards(self) -> None:
        self.run_cli("novo", "Nova/Comercial/Vendas/Painel A")         # company without identity -> padrao
        dash = self.tmp / "dashboards/nova/comercial/vendas/painel-a"
        report = json.loads(next(dash.glob("2-power-bi/*.Report/definition/report.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["themeCollection"]["customTheme"]["name"], "padrao-theme.json")
        # the analyst creates the company identity (the AI fills trabalho-da-ia/identidade.toml)
        shutil.copytree(self.tmp / "identidade-visual/acme", self.tmp / "identidade-visual/nova")
        code, out = self.run_cli("identidade", "nova")
        self.assertEqual(code, 0, out)
        self.assertIn("painel-a", out)
        report = json.loads(next(dash.glob("2-power-bi/*.Report/definition/report.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["themeCollection"]["customTheme"]["name"], "nova-theme.json")
        reg = next(dash.glob("2-power-bi/*.Report/StaticResources/RegisteredResources"))
        self.assertEqual([f.name for f in reg.iterdir()], ["nova-theme.json"])
        self.run_cli("novo", "Nova/Comercial/Vendas/Painel B")         # new dashboards get it directly
        dash_b = self.tmp / "dashboards/nova/comercial/vendas/painel-b"
        self.assertTrue(next(dash_b.glob("2-power-bi/*.Report/StaticResources/RegisteredResources/nova-theme.json")))


class TestRefactor(Sandbox):
    def test_pbit_extraction_and_refactor(self) -> None:
        inbox = self.tmp / "refatorar/acme/financeiro/contas-a-receber/aging"
        inbox.mkdir(parents=True)
        make_pbit(inbox / "Aging.pbit")
        (inbox / "notas.md").write_text("O financeiro usa este relatório toda segunda.", encoding="utf-8")
        code, out = self.run_cli("refatorar")
        self.assertEqual(code, 0, out)
        dash = self.tmp / "dashboards/acme/financeiro/contas-a-receber/aging"
        self.assertTrue((dash / "2-power-bi/Aging.pbip").exists())                   # openable right away
        legacy = dash / "trabalho-da-ia/legado"
        self.assertTrue((legacy / "original.pbit").exists())
        self.assertTrue((legacy / "PLANO.md").exists())
        summary = (legacy / "extracao/summary.md").read_text(encoding="utf-8")
        self.assertIn("Auto date/time", summary)
        self.assertIn("bidirecional", summary)
        self.assertIn("etapas de Power Query", summary)
        self.assertIn("Observacao", summary)  # unused column detected
        self.assertIn("Telefone", summary)
        pq = (legacy / "extracao/power-query.md").read_text(encoding="utf-8")
        self.assertNotIn("10.0.0.15", pq)  # redacted
        self.assertTrue((dash / "1-seu-pedido/anexos/documentos/legado-notas.md").exists())
        self.assertFalse(inbox.exists())  # inbox cleaned

        data = json.loads((legacy / "extracao/extraction.json").read_text(encoding="utf-8"))
        self.assertEqual(data["analysis"]["fact_tables"], ["Vendas"])

    def test_placeholder_path_is_not_refactored(self) -> None:
        ph = self.tmp / "refatorar/nome-da-empresa/nome-da-area/nome-da-subarea/nome-do-dashboard"
        self.assertTrue(ph.is_dir())                                   # ships with the repository
        make_pbit(ph / "Antigo.pbit")
        code, out = self.run_cli("refatorar")
        self.assertIn("renomeie as pastas", out)
        self.assertFalse((self.tmp / "dashboards/nome-da-empresa").exists())


class TestSecurity(Sandbox):
    def test_scanner_blocks_secrets_and_data(self) -> None:
        (self.tmp / "a.sql").write_text("-- conn: Server=x;User Id=sa;Password=SuperSecret1;\n", encoding="utf-8")  # pbw:allow-secret
        (self.tmp / "b.pbix").write_bytes(b"PK\x03\x04data")
        (self.tmp / "conexoes/erp.local.toml").write_text("[parameters]\n", encoding="utf-8")
        hits = secrets.scan(self.tmp, files=[self.tmp / "a.sql", self.tmp / "b.pbix",
                                             self.tmp / "conexoes/erp.local.toml"])
        rules = {h.rule for h in hits}
        self.assertIn("SEC001", rules)
        self.assertIn("SEC101", rules)
        self.assertIn("SEC102", rules)

    def test_allow_marker(self) -> None:
        (self.tmp / "doc.md").write_text("Password=example123 pbw:allow-secret\n", encoding="utf-8")
        self.assertEqual(secrets.scan(self.tmp, files=[self.tmp / "doc.md"]), [])


class TestTmdl(unittest.TestCase):
    def test_example_model_parses(self) -> None:
        defs = list((REPO / "dashboards").glob("*/*/*/*/2-power-bi/*.SemanticModel/definition"))
        self.assertTrue(defs, "example dashboard missing")
        model = tmdl.parse_model(defs[0])
        names = {t.name for t in model.tables}
        self.assertTrue({"_Medidas", "Calendario", "_Documentacao", "_Cargas"} <= names)
        self.assertTrue(all(m.description for _, m in model.measures))


class TestExampleIsGoverned(unittest.TestCase):
    def test_repository_validates(self) -> None:
        import os
        cwd = Path.cwd()
        os.chdir(REPO)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                code = cli.main(["validar"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0, buf.getvalue())


class TestPbitRead(unittest.TestCase):
    def test_extract_without_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.pbit"
            make_pbit(p)
            ex, analysis = pbit.extract(p, do_redact=False)
            self.assertEqual(len(ex.pages), 1)
            self.assertIn("10.0.0.15", ex.tables[0]["partitions"][0]["expression"])
            self.assertIn("Clientes.Nome", ex.pages[0]["visuals"][0]["fields"])


if __name__ == "__main__":
    unittest.main()
