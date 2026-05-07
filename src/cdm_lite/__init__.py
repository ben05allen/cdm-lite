import datetime

from cdm_models.cdm_base_staticdata_party_CounterpartyRoleEnum_schema import CounterpartyRoleEnum
from cdm_models.cdm_base_staticdata_party_PayerReceiver_schema import PayerReceiver
from cdm_models.cdm_base_datetime_PeriodEnum_schema import PeriodEnum
from cdm_models.cdm_base_datetime_RollConventionEnum_schema import RollConventionEnum
from cdm_models.cdm_base_staticdata_party_Party_schema import Party
from cdm_models.cdm_base_staticdata_party_PartyIdentifier_schema import PartyIdentifier
from cdm_models.cdm_product_asset_InterestRatePayout_schema import InterestRatePayout
from cdm_models.cdm_base_datetime_AdjustableDate_schema import AdjustableDate
from cdm_models.cdm_base_datetime_daycount_metafields_FieldWithMetaDayCountFractionEnum_schema import (
    FieldWithMetaDayCountFractionEnum,
)
from cdm_models.cdm_product_asset_RateSpecification_schema import RateSpecification
from cdm_models.cdm_base_datetime_CalculationPeriodFrequency_schema import CalculationPeriodFrequency
from cdm_models.cdm_product_common_schedule_CalculationPeriodDates_schema import (
    CalculationPeriodDates,
)
from cdm_models.cdm_base_staticdata_identifier_AssignedIdentifier_schema import (
    AssignedIdentifier,
)
from cdm_models.cdm_event_common_TradeIdentifier_schema import TradeIdentifier
from cdm_models.com_rosetta_model_metafields_FieldWithMetaString_schema import (
    FieldWithMetaString,
)


def make_party(party_id: str, name: str) -> Party:

    field_party_id = FieldWithMetaString(value=party_id)
    field_name = FieldWithMetaString(value=name)

    party_identifier = PartyIdentifier(identifier=field_party_id)

    return Party(partyId=[party_identifier], name=field_name)


def make_trade_identifier(trade_ref: str, version: int = 1) -> TradeIdentifier:

    return TradeIdentifier(
        assignedIdentifier=[
            AssignedIdentifier(
                identifier=FieldWithMetaString(value=trade_ref),
                version=version,
            )
        ]
    )


def main() -> None:

    party_a = make_party("LEI-PARTY-A", "Bank Alpha")
    party_b = make_party("LEI-PARTY-B", "Pension Fund Beta")
    party_c = make_party("LEI-PARTY-C", "Dealer Gamma")

    print(party_a)

    fixed_leg = InterestRatePayout(
        rateSpecification={"fixedRate": {"initialRate": {"value": 0.035, "unit": {"currency": {"value": "USD"}}}}},
        dayCountFraction={
            "value": "ACT/360",
            "meta": {"scheme": "http://www.fpml.org/coding-scheme/day-count-fraction"},
        },
        calculationPeriodDates={
            "startDate": AdjustableDate(unadjustedDate=datetime.date(2024, 1, 15)),
            "endDate": AdjustableDate(unadjustedDate=datetime.date(2029, 1, 15)),
            "calculationPeriodFrequency": CalculationPeriodFrequency(
                periodMultiplier=6,
                period=PeriodEnum.M,
                rollConvention=RollConventionEnum._15,
            ),
        },
        payerReceiver=PayerReceiver(payer=CounterpartyRoleEnum.party1, receiver=CounterpartyRoleEnum.party2),
    )

    # Floating leg
    floating_leg = InterestRatePayout(
        rateSpecification={
            "floatingRate": {
                "rateOption": {
                    "floatingRateIndex": {
                        "value": "USD-SOFR-OIS-COMPOUND",
                        "meta": {"scheme": "http://www.fpml.org/coding-scheme/floating-rate-index"},
                    },
                    "indexTenor": {"periodMultiplier": 3, "period": PeriodEnum.M},
                },
                "resetDates": {
                    "calculationPeriodDatesReference": {"externalReference": "floatingCalcPeriod"},
                    "resetFrequency": {"periodMultiplier": 3, "period": PeriodEnum.M},
                },
            }
        },
        dayCountFraction={
            "value": "ACT/360",
            "meta": {"scheme": "http://www.fpml.org/coding-scheme/day-count-fraction"},
        },
        calculationPeriodDates={
            "startDate": AdjustableDate(unadjustedDate=datetime.date(2024, 1, 15)),
            "endDate": AdjustableDate(unadjustedDate=datetime.date(2029, 1, 15)),
            "calculationPeriodFrequency": CalculationPeriodFrequency(
                periodMultiplier=3,
                period=PeriodEnum.m,
                rollConvention=RollConventionEnum._15,
            ),
        },
        payerReceiver=PayerReceiver(payer=CounterpartyRoleEnum.party2, receiver=CounterpartyRoleEnum.party1),
    )
