-- @table: Fato Titulos
-- @description: Parcelas de títulos a receber (abertas e liquidadas), sem cancelados.
-- @grain: 1 linha por parcela de título
SELECT
    t.id_parcela                                   AS id_parcela,
    t.id_cliente                                   AS id_cliente,
    t.id_filial                                    AS id_filial,
    CAST(t.dt_emissao    AS date)                  AS [Data Emissão],
    CAST(t.dt_vencimento AS date)                  AS [Data Vencimento],
    CAST(t.dt_pagamento  AS date)                  AS [Data Pagamento],
    CAST(t.vl_parcela AS decimal(18, 2))           AS [Valor Parcela],
    CAST(t.vl_pago    AS decimal(18, 2))           AS [Valor Pago],
    CAST(t.vl_parcela - t.vl_pago AS decimal(18, 2)) AS [Saldo Aberto],
    CASE WHEN t.dt_pagamento IS NULL
         THEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) ELSE 0 END AS [Dias Atraso],
    CASE
        WHEN t.dt_pagamento IS NOT NULL                                   THEN 'Liquidado'
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 0  THEN 'A vencer'
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 30 THEN '1–30'
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 60 THEN '31–60'
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 90 THEN '61–90'
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 180 THEN '91–180'
        ELSE '> 180'
    END                                            AS [Faixa Atraso],
    CASE
        WHEN t.dt_pagamento IS NOT NULL                                   THEN 9
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 0  THEN 0
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 30 THEN 1
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 60 THEN 2
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 90 THEN 3
        WHEN DATEDIFF(day, t.dt_vencimento, CAST(GETDATE() AS date)) <= 180 THEN 4
        ELSE 5
    END                                            AS [Faixa Ordem]
FROM bi.vw_titulos_receber AS t
WHERE t.status <> 'C'
