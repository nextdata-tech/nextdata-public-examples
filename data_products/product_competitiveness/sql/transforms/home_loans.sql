CREATE OR REPLACE TABLE HOME_LOAN_RATES AS
    WITH CTE_ANZ_HOME_LOANS AS (
        SELECT
            'ANZ' as bank,
            'Fixed Home Loan' as product,
            regexp_extract_all(baserate_obj.value:tiername1::string, '\\d+')[0]::int as loan_term, -- TODO: Figure out how to tighthen this
            iff(endswith(baserate_obj.value:tiername1, '<80%'), 0, 80) as min_lvr,
            iff(endswith(baserate_obj.value:tiername1, '<80%'), 80, 100) as max_lvr,
            0 as min_loan,
            null as max_loan,
            baserate_obj.value:ratevalue::decimal(6,2) as rate
        FROM
            ANZ_PRODUCTS,
            LATERAL FLATTEN(INPUT => SUBSECTION) as subsection_obj,
            LATERAL FLATTEN(INPUT => subsection_obj.value:baserate) as baserate_obj
        WHERE
            subsection_obj.value:code::string in ('HOOHLSIR', 'HOOFR')
            and baserate_obj.value:ratetype::string = 'Principal and Interest'

    ),

    CTE_MACQUARIE_HOME_LOANS AS (
        select
            'Macquarie' as bank,
            'Fixed Mortgage Basic' as product,
            regexp_extract_all(title, '_([0-9]+)year_', 1, 1, 'e')[0]::int as loan_term,
            case
                when contains(title, 'lte70') then 0
                when contains(title, 'lte80') then 70
                when contains(title, 'lte90') then 80
            end as min_lvr,
            case
                when contains(title, 'lte70') then 70
                when contains(title, 'lte80') then 80
                when contains(title, 'lte90') then 100
            end as max_lvr,
            0 as min_loan,
            null as max_loan,
            cast(rtrim(value, '% pa') as decimal(6, 2)) as rate
        from MACQUARIE_HOME_LOANS
        where
            title like 'mort_basic_fix_%'
            and endswith(title, '0_rate')
        order by
            loan_term,
            min_lvr
    ),

    CTE_RAW_WESTPAC_HOME_LOANS AS (
        SELECT
            product_obj.value:ProductId::string AS product_id,
            CASE PortfolioId
                WHEN 'HLLVR3' THEN 0
                WHEN 'HL' THEN 70
                WHEN 'HLLVR5' THEN 80
            END AS min_lvr,
            CASE PortfolioId
                WHEN 'HLLVR3' THEN 70
                WHEN 'HL' THEN 80
                WHEN 'HLLVR5' THEN 100
            END AS max_lvr,
            product_obj.value:Rates AS rates,
            product_codes.value::string as product_code,
            rates[product_code]:PRODUCT::string as product,
            rates[product_code]:RATECODE::string as rate_code,
            rates[product_code]:Std_Rate::decimal(6,2) as rate
        FROM WESTPAC_HOME_LOANS,
            LATERAL FLATTEN(Products) product_obj,
            LATERAL FLATTEN(OBJECT_KEYS(product_obj.value:Rates)) product_codes
    ),

    CTE_REFINED_WESTPAC_HOME_LOANS as (
        select
            product_id,
            regexp_extract_all(product_id, '[0-9]Year([A-Za-z]+)')[0]::string as product,
            regexp_extract_all(product_id, '^[0-9]')[0]::int as loan_term,
            endswith(product_id, '-InterestOnly') as interest_only,
            case
                when endswith(product, '<$150k') then 0
                when endswith(product, '$150k-$250k') then 150000
                when endswith(product, '$250k-$500k') then 250000
                when endswith(product, '$500k-$750k') then 500000
                when endswith(product, '$750k-$1mil') then 750000
                when endswith(product, '$1mil+') then 1000000
            end as min_loan,
            case
                when endswith(product, '<$150k') then 150000
                when endswith(product, '$150k-$250k') then 250000
                when endswith(product, '$250k-$500k') then 500000
                when endswith(product, '$500k-$750k') then 750000
                when endswith(product, '$750k-$1mil') then 1000000
            end as max_loan,
            rate,
            min_lvr,
            max_lvr
        from CTE_RAW_WESTPAC_HOME_LOANS
        where rate_code like 'PAHLFX%'  -- Include fixed term loans only for now..
            and rate_code not like '%0' -- Include fixed term loans above $150k

    ),

    CTE_WESTPAC_HOME_LOANS AS (
        select
            'Westpac' as bank,
            product,
            loan_term,
            min_lvr,
            max_lvr,
            min(min_loan) as min_loan,
            max(max_loan) as max_loan,
            rate
        from CTE_REFINED_WESTPAC_HOME_LOANS
        where
            not interest_only
        group by
            product,
            loan_term,
            min_lvr,
            max_lvr,
            rate
        order by
            loan_term,
            min_lvr,
            min_loan
    )

    SELECT * FROM CTE_WESTPAC_HOME_LOANS
    UNION ALL
    SELECT * FROM CTE_ANZ_HOME_LOANS
    UNION ALL
    SELECT * FROM CTE_MACQUARIE_HOME_LOANS
