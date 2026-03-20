CREATE OR REPLACE TABLE TERM_DEPOSITS AS
    WITH CTE_RAW_ANZ_TERM_DEPOSITS AS (
        SELECT
            deposit_accounts.value:name::string as name,
            'ANZ' as bank,
            5000 as min_amount,
            1999999 as max_amount,
            regexp_extract_all(term_deposits.value:tiername1, '^([0-9]+)', 1, 1, 'e')[0]::int as min_term,
            regexp_extract_all(term_deposits.value:tiername1, '([0-9]+) months', 1, 1, 'e')[0]::int as max_term,
            max(iff(term_deposits.value:ratetype = 'Monthly Interest', term_deposits.value:ratevalue, null)::decimal(4,2)) as monthly_rate,
            max(iff(term_deposits.value:ratetype = 'Annual Interest', term_deposits.value:ratevalue, null)::decimal(4,2)) as annual_rate,
            max(iff(term_deposits.value:ratetype = 'Interest at Maturity', term_deposits.value:ratevalue, null)::decimal(4,2)) as maturity_rate
        FROM
            ANZ_PRODUCTS,
            LATERAL FLATTEN(SUBSECTION) as deposit_accounts,
            LATERAL FLATTEN(deposit_accounts.value:baserate) as term_deposits
        WHERE
            isactive = '1'
            and isfordisplay = '1'
            and "name" = 'Deposit accounts'
            and deposit_accounts.value:isactive = '1'
            and deposit_accounts.value:isfordisplay = '1'
            and deposit_accounts.value:name in ('ANZ Term Deposit', 'ANZ Advance Notice Term Deposit')
            and term_deposits.value:tiername1 not like '% (NOT IN USE)'
            and term_deposits.value:ratevalue != 'blank'
            and term_deposits.value:ratetype in ('Interest at Maturity', 'Monthly Interest', 'Annual Interest')
            and term_deposits.value:tiername1 not like '% days %'
        GROUP BY
            name,
            min_term,
            max_term
        ORDER BY
            name,
            min_term
    ),

    CTE_ANZ_TERM_DEPOSITS AS (
        SELECT
            name,
            bank,
            min_amount,
            max_amount,
            min_term,
            max_term,
            monthly_rate,
            annual_rate,
            -- impute missing maturity rate when term is 12 months
            case when min_term = 12 then annual_rate else maturity_rate end as maturity_rate
        FROM CTE_RAW_ANZ_TERM_DEPOSITS
    ),

    CTE_RAW_MACQUARIE_TERM_DEPOSITS as (
        select
            title as name,
            'Macquarie' as bank,
            case when endswith(title, '_1m') then 1000001 else 5000 end as min_amount,
            case when endswith(title, '_1m') then null else 1000000 end as max_amount,
            case
                when title regexp '.+[0-9]_months?.*' then regexp_extract_all(title, '([0-9])_month(s?)', 1, 1, 'e')[0]::int
                when title regexp '.+[0-9]_years?.*' then regexp_extract_all(title, '([0-9])_year(s?)', 1, 1, 'e')[0]::int * 12
            end as min_term,
            case when contains(title, '_monthly_') then value::decimal(4, 2) end as monthly_rate,
            case when contains(title, '_annually_') then value::decimal(4, 2) end as annual_rate,
            case when contains(title, '_maturity_') then value::decimal(4, 2) end as maturity_rate
        from MACQUARIE_TERM_DEPOSITS
        where
            title like 'term_deposit_macquarie_bank_monthly_%'
                or title like 'term_deposit_macquarie_bank_annually_%'
                or title like 'term_deposit_macquarie_bank_maturity_%'
    ),

    CTE_MACQUARIE_TERM_DEPOSITS as (
        select
            'term-deposit-' || min_term || 'months-' || min_amount as name,
            'Macquarie' as bank,
            min_amount,
            max_amount,
            min_term,
            lead(min_term) over (partition by min_amount order by min_term) as max_term,
            max(monthly_rate) as monthly_rate,
            max(annual_rate) as annual_rate,
            max(maturity_rate) as maturity_rate
        from CTE_RAW_MACQUARIE_TERM_DEPOSITS
        group by bank, min_amount, max_amount, min_term
        order by
            min_term,
            min_amount
    ),

    CTE_RAW_WESTPAC_TERM_DEPOSITS as (
        select
            regexp_extract_all(product_id, '^[a-zA-Z]+')[0] as product_name,
            5000 as min_amount,
            -- Max amount is $2M according to website
            2000000 as max_amount,
            iff(min_term = '', '0', min_term)::int as min_term,
            -- Max term is 5 years according to website
            iff(max_term = '', '600', max_term)::int as max_term,
            monthly_rate::decimal(4,2) as monthly_rate,
            maturity_rate::decimal(4,2) as maturity_rate
        FROM PRODUCT_COMPETITIVENESS.WESTPAC_TERM_DEPOSITS
        WHERE
            min_term != ''
            -- Remove terms less than 1 month for simplicity
            and iff(min_term = '', '0', min_term)::int >= 1
            -- Remove Hot Rate deals which no longer exist
            and rate_code not like 'HR%'
            -- Remove terms un-bounded max_terms
            and max_term != ''
    ),

    WESTPAC_TERM_DEPOSITS as (
        SELECT
            product_name ||'-' || min(min_amount) || '~' || min_term as name,
            'Westpac' as bank,
            min(min_amount) as min_amount,
            max(max_amount) as max_amount,
            min_term,
            max(max_term) as max_term,
            cast(
                case product_name
                    when 'DigitalPromo' then maturity_rate
                    when 'FixedInterestRate' then maturity_rate - 0.05
                    else monthly_rate
                end
                as decimal(4, 2)
            ) as monthly_rate,
            -- westpac only offers an annual rate after 12 months
            cast(case when min_term > 12 then maturity_rate end as decimal(4, 2)) as annual_rate,
            -- westpac does not offer interest at maturity past 12 months
            cast(case when min_term <= 12 then maturity_rate end as decimal(4, 2)) as maturity_rate
        FROM CTE_RAW_WESTPAC_TERM_DEPOSITS
        WHERE min_term >= 1
            -- Max amount should be $2M
            and max_amount <= 2000000
        GROUP BY
            product_name,
            min_term,
            maturity_rate,
            monthly_rate
        ORDER BY
            min_term,
            min_amount
    )

    SELECT * FROM WESTPAC_TERM_DEPOSITS
    UNION ALL
    SELECT * FROM CTE_ANZ_TERM_DEPOSITS
    UNION ALL
    SELECT * FROM CTE_MACQUARIE_TERM_DEPOSITS
