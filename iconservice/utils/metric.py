# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway


class PrometheusMetric(object):
    """
    Prometheus Metric Class
    Push ICON monitoring metrics to Prometheus PushGateway
    """
    # PushGateway URI
    pushgateway = "localhost:9091"

    # metrics
    block_height = Gauge('icon_block_height', 'Block height')
    total_supply = Gauge('icon_total_supply', 'Total supply of ICX')
    icx_issue_amount = Gauge('icon_icx_issue_amount', 'Issued ICX amount')
    iiss_total_delegation = Gauge('icon_iiss_total_delegataion', 'Total delegation amount')
    iiss_representive_incentive = \
        Gauge('icon_iiss_representative_incentive', 'Monthly incentive amount to representative')
    iiss_delegation_reward_rate = \
        Gauge('icon_iiss_delegation_reward_rate', 'Yearly reward rate for delegation')

    # register metrics to registry
    iiss_registry = CollectorRegistry()
    iiss_registry.register(block_height)
    iiss_registry.register(total_supply)
    iiss_registry.register(icx_issue_amount)
    iiss_registry.register(iiss_total_delegation)
    iiss_registry.register(iiss_representive_incentive)
    iiss_registry.register(iiss_delegation_reward_rate)

    @classmethod
    def push_iiss(cls) -> None:
        """
        Push ICON IISS monitoring metrics to Prometheus PushGateway
        """
        push_to_gateway(cls.pushgateway, job='icon_iiss', registry=cls.iiss_registry)

    @classmethod
    def set_block_height(cls, value) -> None:
        """
        Set block height
        :param value: block_height
        """
        cls.block_height.set(value)

    @classmethod
    def set_total_supply(cls, value) -> None:
        """
        Set ICX total supply
        :param value: total supply
        """
        cls.total_supply.set(value)

    @classmethod
    def set_icx_issue_amount(cls, value) -> None:
        """
        Set issued ICX amount
        :param value: issued ICX amount
        :return:
        """
        cls.icx_issue_amount.set(value)

    @classmethod
    def set_iiss_total_delegation(cls, value) -> None:
        """
        Set total IISS delegation amount
        :param value: total delegation amount
        """
        cls.iiss_total_delegation.set(value)

    @classmethod
    def set_iiss_representative_incentive(cls, value) -> None:
        """
        Set IISS incentive amount to representative
        :param value: IISS incentive amount
        """
        cls.iiss_representive_incentive.set(value)

    @classmethod
    def set_iiss_delegation_reward_rate(cls, value) -> None:
        """
        Set IISS delegation reward rate
        :param value: IISS delegation reward rate
        """
        cls.iiss_delegation_reward_rate.set(value)
