from cdm_models.cdm_base_staticdata_party_CounterpartyRoleEnum_schema import CounterpartyRoleEnum
from cdm_models.cdm_base_staticdata_party_PayerReceiver_schema import PayerReceiver
from cdm_models.cdm_base_datetime_PeriodExtendedEnum_schema import PeriodExtendedEnum
from cdm_models.cdm_base_datetime_RollConventionEnum_schema import RollConventionEnum
from cdm_models.cdm_base_staticdata_party_Party_schema import Party
from cdm_models.cdm_base_staticdata_party_PartyIdentifier_schema import PartyIdentifier
from cdm_models.cdm_product_asset_InterestRatePayout_schema import InterestRatePayout
from cdm_models.cdm_base_datetime_AdjustableDate_schema import AdjustableDate
from cdm_models.cdm_base_datetime_AdjustableOrRelativeDate_schema import AdjustableOrRelativeDate
from cdm_models.cdm_base_datetime_daycount_metafields_FieldWithMetaDayCountFractionEnum_schema import (
    FieldWithMetaDayCountFractionEnum,
)
from cdm_models.cdm_base_datetime_daycount_DayCountFractionEnum_schema import DayCountFractionEnum
from cdm_models.cdm_product_asset_RateSpecification_schema import RateSpecification
from cdm_models.cdm_product_asset_FixedRateSpecification_schema import FixedRateSpecification
from cdm_models.cdm_product_asset_FloatingRateSpecification_schema import FloatingRateSpecification
from cdm_models.cdm_product_common_schedule_RateSchedule_schema import RateSchedule
from cdm_models.cdm_observable_asset_metafields_ReferenceWithMetaPriceSchedule_schema import (
    ReferenceWithMetaPriceSchedule,
)
from cdm_models.cdm_observable_asset_metafields_ReferenceWithMetaInterestRateIndex_schema import (
    ReferenceWithMetaInterestRateIndex,
)
from cdm_models.com_rosetta_model_metafields_MetaFields_schema import MetaFields
from cdm_models.cdm_base_datetime_CalculationPeriodFrequency_schema import CalculationPeriodFrequency
from cdm_models.cdm_product_common_schedule_CalculationPeriodDates_schema import (
    CalculationPeriodDates,
)
from cdm_models.cdm_product_common_schedule_ResetDates_schema import ResetDates
from cdm_models.cdm_product_common_schedule_ResetFrequency_schema import ResetFrequency
from cdm_models.cdm_product_common_schedule_metafields_ReferenceWithMetaCalculationPeriodDates_schema import (
    ReferenceWithMetaCalculationPeriodDates,
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
        rateSpecification=RateSpecification(
            FixedRateSpecification=FixedRateSpecification(
                rateSchedule=RateSchedule(price=ReferenceWithMetaPriceSchedule(externalReference="fixedRate-1"))
            )
        ),
        dayCountFraction=FieldWithMetaDayCountFractionEnum(
            value=DayCountFractionEnum.ACT_360,
            meta=MetaFields(scheme="http://www.fpml.org/coding-scheme/day-count-fraction"),
        ),
        calculationPeriodDates=CalculationPeriodDates(
            effectiveDate=AdjustableOrRelativeDate(adjustableDate=AdjustableDate(unadjustedDate="2024-01-15")),
            terminationDate=AdjustableOrRelativeDate(adjustableDate=AdjustableDate(unadjustedDate="2029-01-15")),
            calculationPeriodFrequency=CalculationPeriodFrequency(
                periodMultiplier=6,
                period=PeriodExtendedEnum.M,
                rollConvention=RollConventionEnum.FIELD_15,
            ),
        ),
        payerReceiver=PayerReceiver(payer=CounterpartyRoleEnum.PARTY1, receiver=CounterpartyRoleEnum.PARTY2),
    )

    # Floating leg
    floating_leg = InterestRatePayout(
        rateSpecification=RateSpecification(
            FloatingRateSpecification=FloatingRateSpecification(
                rateOption=ReferenceWithMetaInterestRateIndex(globalReference="USD-SOFR-OIS-COMPOUND")
            )
        ),
        resetDates=ResetDates(
            calculationPeriodDatesReference=ReferenceWithMetaCalculationPeriodDates(
                externalReference="floatingCalcPeriod"
            ),
            resetFrequency=ResetFrequency(periodMultiplier=3, period=PeriodExtendedEnum.M),
        ),
        dayCountFraction=FieldWithMetaDayCountFractionEnum(
            value=DayCountFractionEnum.ACT_360,
            meta=MetaFields(scheme="http://www.fpml.org/coding-scheme/day-count-fraction"),
        ),
        calculationPeriodDates=CalculationPeriodDates(
            effectiveDate=AdjustableOrRelativeDate(adjustableDate=AdjustableDate(unadjustedDate="2024-01-15")),
            terminationDate=AdjustableOrRelativeDate(adjustableDate=AdjustableDate(unadjustedDate="2029-01-15")),
            calculationPeriodFrequency=CalculationPeriodFrequency(
                periodMultiplier=3,
                period=PeriodExtendedEnum.M,
                rollConvention=RollConventionEnum.FIELD_15,
            ),
        ),
        payerReceiver=PayerReceiver(payer=CounterpartyRoleEnum.PARTY2, receiver=CounterpartyRoleEnum.PARTY1),
    )
    print(fixed_leg)
    print(floating_leg)
    print(party_b, party_c)
