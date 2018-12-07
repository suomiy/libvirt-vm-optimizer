from copy import deepcopy
from operation.data import Topology
import math


def get_cpus_to_pin(cell, pin_count, prefer_hyperthread_pinning):
    """

    :param cell: NUMA node
    :param pin_count: attempts to pin pin_count number of cpus to this cell
    :param prefer_hyperthread_pinning: pins sibling (hyperthreading) threads if possible
    :return: cpus to pin and results topology of this cell
    """
    cell_cpus = cell.cpus
    cpus_to_pin = {}

    if prefer_hyperthread_pinning:
        cpus_to_pin = _get_pinning_with_siblings(cell_cpus, pin_count)
    else:
        while True:
            # try to pin cpus in rounds to minimize siblings
            first_cell_cpus_next_round = {k: v for (k, v) in cell_cpus.items() if k not in cpus_to_pin}
            to_pin = _get_pinning_without_siblings(first_cell_cpus_next_round, pin_count - len(cpus_to_pin))

            cpus_to_pin.update(to_pin)
            if not to_pin:  # no more cpus
                break

    max_sibling_count = 0
    # remove unnecessary siblings and resolve topology
    for key, cpu in cpus_to_pin.items():
        cpu.siblings = set(filter(lambda x: x in cpus_to_pin.keys(), cpu.siblings))
        max_sibling_count = max(max_sibling_count, len(cpu.siblings))

    threads = max_sibling_count + 1
    cores = math.ceil(len(cpus_to_pin) / threads)
    return cpus_to_pin, Topology(1, cores, threads)


def _get_pinning_without_siblings(cell_cpus, pin_count):
    cpu_ids = list(sorted(cell_cpus.keys()))

    cpus_to_pin = {}

    while pin_count > 0:
        if len(cpu_ids) == 0:
            break
        pin_cpu = cell_cpus.get(cpu_ids.pop(0))

        if not set(cpus_to_pin).intersection(pin_cpu.siblings):  # append only if it's siblings are not present
            cpus_to_pin[pin_cpu.id] = deepcopy(pin_cpu)
            pin_count -= 1

    return cpus_to_pin


def _get_pinning_with_siblings(cell_cpus, pin_count):
    cpu_ids = list(sorted(cell_cpus.keys()))
    add_pin_idx = 0

    cpus_to_pin = {}

    while pin_count > 0:
        if len(cpu_ids) == 0:
            break

        # get lowest id or pin sibling
        pin_cpu = cell_cpus.get(cpu_ids.pop(add_pin_idx))

        # pin
        cpus_to_pin[pin_cpu.id] = deepcopy(pin_cpu)

        # resolve new sibling idx
        for idx, cpu_id in enumerate(cpu_ids):
            if cpu_id in pin_cpu.siblings:
                add_pin_idx = idx
                break
        else:
            add_pin_idx = 0

        pin_count -= 1

    return cpus_to_pin