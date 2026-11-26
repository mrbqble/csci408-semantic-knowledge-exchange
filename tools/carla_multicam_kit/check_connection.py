#!/usr/bin/env python3
"""Проверка, что Python видит сервер CARLA. Печатает версии, карту и доступные карты."""

import argparse
import sys
import time

import carla


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--wait", type=int, default=120, help="Сколько секунд ждать запуска сервера")
    args = p.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(10.0)

    deadline = time.time() + args.wait
    while True:
        try:
            server = client.get_server_version()
            break
        except RuntimeError:
            if time.time() > deadline:
                print(f"[ОШИБКА] Сервер на {args.host}:{args.port} не отвечает {args.wait} c.")
                print("Проверь, что окно CARLA открыто и карта загрузилась.")
                sys.exit(1)
            print("Жду сервер CARLA...")
            time.sleep(5)

    print(f"Клиент: {client.get_client_version()}")
    print(f"Сервер: {server}")
    if client.get_client_version().split("-")[0] != server.split("-")[0]:
        print("[ВНИМАНИЕ] Версии клиента и сервера отличаются, возможны ошибки.")

    world = client.get_world()
    print(f"Текущая карта: {world.get_map().name}")
    print("Доступные карты:")
    for m in sorted(client.get_available_maps()):
        print("  ", m.split("/")[-1])
    print("\nВсё работает.")


if __name__ == "__main__":
    main()
