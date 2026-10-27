select *
  from {{ source('raw', 'kalshi_chess_trades') }}
  qualify row_number() over (
      partition by trade_id
      order by _ingested_at desc
  ) = 1