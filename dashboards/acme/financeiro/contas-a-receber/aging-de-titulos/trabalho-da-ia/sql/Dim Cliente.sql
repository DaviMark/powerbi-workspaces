-- @table: Dim Cliente
-- @description: Clientes com pelo menos um título (pessoa jurídica).
-- @grain: 1 linha por cliente
SELECT
    c.id_cliente    AS id_cliente,
    c.nome_fantasia AS [Cliente],
    c.segmento      AS [Segmento],
    c.uf            AS [UF]
FROM bi.vw_clientes AS c
WHERE EXISTS (SELECT 1 FROM bi.vw_titulos_receber t WHERE t.id_cliente = c.id_cliente)
