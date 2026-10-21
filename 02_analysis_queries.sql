USE logistics_portfolio;

-- 1. Shipment status overview
SELECT shipment_status, COUNT(*) AS shipment_count
FROM shipments
GROUP BY shipment_status
ORDER BY shipment_count DESC;

-- 2. On-time delivery rate by carrier (delivered rows with valid transit duration)
SELECT
    c.carrier_name,
    COUNT(*) AS delivered_shipments,
    SUM(CASE WHEN s.actual_transit_days <= s.promised_delivery_days THEN 1 ELSE 0 END) AS on_time_shipments,
    ROUND(100.0 * SUM(CASE WHEN s.actual_transit_days <= s.promised_delivery_days THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_rate_pct
FROM shipments s
JOIN carriers c ON s.carrier_id = c.carrier_id
WHERE s.shipment_status = 'Delivered'
  AND s.actual_transit_days IS NOT NULL
  AND s.promised_delivery_days IS NOT NULL
GROUP BY c.carrier_name
ORDER BY on_time_rate_pct DESC;

-- 3. Average freight cost per shipment by shipping mode
SELECT shipping_mode,
       COUNT(freight_cost_inr) AS shipments_with_cost,
       ROUND(AVG(freight_cost_inr), 2) AS avg_freight_cost_inr
FROM shipments
GROUP BY shipping_mode
ORDER BY avg_freight_cost_inr DESC;

-- 4. Monthly shipments and average delay
SELECT DATE_FORMAT(dispatch_date, '%Y-%m') AS dispatch_month,
       COUNT(*) AS shipment_count,
       ROUND(AVG(delay_days), 2) AS avg_delay_days
FROM shipments
GROUP BY DATE_FORMAT(dispatch_date, '%Y-%m')
ORDER BY dispatch_month;

-- 5. Destination region performance (requires destination location join)
SELECT l.region AS destination_region,
       COUNT(*) AS delivered_shipments,
       ROUND(AVG(s.delay_days), 2) AS avg_delay_days
FROM shipments s
JOIN locations l ON s.destination_location_id = l.location_id
WHERE s.shipment_status = 'Delivered'
GROUP BY l.region
ORDER BY avg_delay_days DESC;

-- Add your own query: compare shipment performance by distance band.
