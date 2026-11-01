"use client";
import { useState } from "react";
import type { BuildingSnapshot, Units } from "../lib/types";
import { area, areaLabel } from "../lib/format";
import { rectangleBounds } from "../site-model";
import Icon from "./Icon";

type Props = {
  snap: BuildingSnapshot;
  units: Units;
  disabled: boolean;
  error: string;
  selected?: string;
  onSelect?: (id: string) => void;
  onCommand: (commands: Record<string, unknown>[], label: string) => void;
  onPlan: () => void;
};
export default function SiteControls({
  snap,
  units,
  disabled,
  error,
  selected,
  onSelect,
  onCommand,
  onPlan,
}: Props) {
  const site = snap.site_layout,
    yard = site?.yard,
    garage = site?.garage;
  const yardBox = yard ? rectangleBounds(yard.polygon) : null,
    garageBox = garage ? rectangleBounds(garage.polygon) : null;
  const [yardWidth, setYardWidth] = useState(
    String(
      Number(
        (yardBox?.width ?? snap.building_program?.width_m ?? 18).toFixed(6),
      ),
    ),
  );
  const [yardDepth, setYardDepth] = useState(
    String(Number((yardBox?.depth ?? 8).toFixed(6))),
  );
  const [garageWidth, setGarageWidth] = useState(
    String(Number((garageBox?.width ?? 3.6).toFixed(6))),
  );
  const [garageDepth, setGarageDepth] = useState(
    String(Number((garageBox?.depth ?? 6).toFixed(6))),
  );
  const [garageSide, setGarageSide] = useState(garage?.side ?? "right");
  const [expanded, setExpanded] = useState(selected ?? "");
  const outdoor = snap.pool?.location === "outdoor";
  return (
    <section className="edit-block site-controls" aria-label="Yard and garage">
      <h3>Yard &amp; garage</h3>
      <p>Shape the outdoor space around your home.</p>
      {error && (
        <p role="alert" className="site-mobile-error">
          {error}
        </p>
      )}
      {yard ? (
        <details open={expanded === yard.id}>
          <summary
            onClick={(event) => {
              event.preventDefault();
              setExpanded(expanded === yard.id ? "" : yard.id);
              onSelect?.(yard.id);
            }}
          >
            Yard{" "}
            <span>
              {areaLabel(
                area(yard.polygon) -
                  yard.holes.reduce((sum, ring) => sum + area(ring), 0),
                units,
              )}{" "}
              landscape
            </span>
          </summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onCommand(
                [
                  {
                    type: "set_yard",
                    yard: {
                      width_m: Number(yardWidth),
                      depth_m: Number(yardDepth),
                    },
                  },
                ],
                "Updating yard",
              );
            }}
          >
            <div className="site-dimensions">
              <label>
                Width (m)
                <input
                  aria-label="Yard width in metres"
                  type="number"
                  required
                  step=".1"
                  min="3"
                  max="100"
                  value={yardWidth}
                  onChange={(e) => setYardWidth(e.target.value)}
                  disabled={disabled}
                />
              </label>
              <label>
                Depth (m)
                <input
                  aria-label="Yard depth in metres"
                  type="number"
                  required
                  step=".1"
                  min="3"
                  max="100"
                  value={yardDepth}
                  onChange={(e) => setYardDepth(e.target.value)}
                  disabled={disabled}
                />
              </label>
            </div>
            <div className="site-edit-actions">
              <button type="submit" disabled={disabled}>
                Apply yard
              </button>
              <button
                type="button"
                disabled={disabled || outdoor}
                onClick={() =>
                  onCommand([{ type: "set_yard", yard: null }], "Removing yard")
                }
              >
                Remove yard
              </button>
            </div>
            {outdoor && (
              <p>Remove the outdoor pool before removing its yard.</p>
            )}
          </form>
        </details>
      ) : (
        <button
          className="site-add"
          disabled={disabled}
          onClick={() =>
            onCommand(
              [{ type: "set_yard", yard: { width_m: null, depth_m: 8 } }],
              "Adding yard",
            )
          }
        >
          <Icon name="plus" size={15} />
          Add a yard
        </button>
      )}
      {garage ? (
        <details open={expanded === garage.id}>
          <summary
            onClick={(event) => {
              event.preventDefault();
              setExpanded(expanded === garage.id ? "" : garage.id);
              onSelect?.(garage.id);
            }}
          >
            Detached garage{" "}
            <span>{areaLabel(area(garage.polygon), units)}</span>
          </summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onCommand(
                [
                  {
                    type: "set_garage",
                    garage: {
                      width_m: Number(garageWidth),
                      depth_m: Number(garageDepth),
                      height_m: garage.height_m,
                      side: garageSide,
                      vehicle_door_width_m: garage.vehicle_door_width_m,
                    },
                  },
                ],
                "Updating garage",
              );
            }}
          >
            <div className="site-dimensions">
              <label>
                Width (m)
                <input
                  aria-label="Garage width in metres"
                  type="number"
                  required
                  step=".1"
                  min={garage.vehicle_door_width_m + 0.6}
                  max="15"
                  value={garageWidth}
                  onChange={(e) => setGarageWidth(e.target.value)}
                  disabled={disabled}
                />
              </label>
              <label>
                Depth (m)
                <input
                  aria-label="Garage depth in metres"
                  type="number"
                  required
                  step=".1"
                  min="5"
                  max="20"
                  value={garageDepth}
                  onChange={(e) => setGarageDepth(e.target.value)}
                  disabled={disabled}
                />
              </label>
            </div>
            <label>
              Side of house
              <select
                aria-label="Garage side"
                value={garageSide}
                onChange={(e) =>
                  setGarageSide(e.target.value as "left" | "right")
                }
                disabled={disabled}
              >
                <option value="right">Right</option>
                <option value="left">Left</option>
              </select>
            </label>
            <div className="site-edit-actions">
              <button type="submit" disabled={disabled}>
                Apply garage
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={() =>
                  onCommand(
                    [{ type: "set_garage", garage: null }],
                    "Removing garage",
                  )
                }
              >
                Remove garage
              </button>
            </div>
          </form>
        </details>
      ) : (
        <button
          className="site-add"
          disabled={disabled}
          onClick={() =>
            onCommand(
              [
                {
                  type: "set_garage",
                  garage: {
                    width_m: 3.6,
                    depth_m: 6,
                    height_m: 2.8,
                    side: "right",
                    vehicle_door_width_m: 2.6,
                  },
                },
              ],
              "Adding garage",
            )
          }
        >
          <Icon name="plus" size={15} />
          Add a garage
        </button>
      )}
      {snap.pool && !outdoor && (
        <>
          <button
            className="site-add"
            disabled={disabled}
            onClick={() =>
              onCommand(
                [
                  {
                    type: "set_outdoor_pool",
                    pool: {
                      water_length_m: snap.pool!.water_length_m,
                      water_width_m: snap.pool!.water_width_m,
                      water_depth_m: snap.pool!.water_depth_m,
                      level: "ground",
                      location: "outdoor",
                    },
                  },
                ],
                "Moving pool outdoors",
              )
            }
          >
            <Icon name="arrow" size={15} />
            Move pool outdoors
          </button>
          <p>The existing indoor pool room stays in the house.</p>
        </>
      )}
      {!snap.pool && (
        <button
          className="site-add"
          disabled={disabled}
          onClick={() =>
            onCommand(
              [
                {
                  type: "set_outdoor_pool",
                  pool: {
                    water_length_m: 8,
                    water_width_m: 3.5,
                    water_depth_m: 1.4,
                    level: "ground",
                    location: "outdoor",
                  },
                },
              ],
              "Adding outdoor pool",
            )
          }
        >
          <Icon name="plus" size={15} />
          Add an outdoor pool
        </button>
      )}
      {outdoor && (
        <button
          className="site-add"
          disabled={disabled}
          onClick={() =>
            onCommand(
              [{ type: "set_outdoor_pool", pool: null }],
              "Removing outdoor pool",
            )
          }
        >
          <Icon name="minus" size={15} />
          Remove outdoor pool
        </button>
      )}
      <button className="site-plan-link" onClick={onPlan}>
        <Icon name="site" size={15} />
        View site plan
        <Icon name="chevron" size={13} />
      </button>
      {(yard || garage) && (
        <p>
          Concept dimensions. Site boundaries and vehicle access need review.
        </p>
      )}
    </section>
  );
}
