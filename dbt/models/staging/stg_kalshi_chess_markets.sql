select *
  from {{ source('raw', 'kalshi_chess_markets') }}
  qualify row_number() over (
      partition by ticker
      order by _ingested_at desc
  ) = 1