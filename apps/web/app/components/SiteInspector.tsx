import type { ReactNode } from "react";
import type { BuildingSnapshot, Units } from "../lib/types";
import { areaLabel, length, title } from "../lib/format";
import {
  findSiteFeature,
  garageQuantities,
  polygonQuantities,
  surfaceQuantities,
} from "../site-selection";
import Icon from "./Icon";

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="property">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function elevation(value: number, units: Units) {
  return `${value < 0 ? "−" : ""}${length(Math.abs(value), units)}`;
}

function volume(value: number, units: Units) {
  return `${(units === "metric" ? value : value / 0.028316846592).toLocaleString("en-US", { maximumFractionDigits: 2 })} ${units === "metric" ? "m³" : "ft³"}`;
}

const wallFinishes = {
  limestone_oak: "Limestone appearance",
  warm_concrete: "Warm concrete appearance",
  white_stucco: "White stucco appearance",
};

/** Read-only quantities and finish descriptions from the selected revision. */
export default function SiteInspector({
  snap,
  featureId,
  units,
}: {
  snap: BuildingSnapshot;
  featureId: string;
  units: Units;
}) {
  const feature = findSiteFeature(snap, featureId);
  if (!feature) return null;
  const site = snap.site_layout;
  const surface =
    feature.kind === "yard"
      ? site?.yard
      : feature.kind === "driveway"
        ? site?.driveway
        : feature.kind === "pool_deck"
          ? site?.pool_deck
          : null;
  const garage = feature.kind === "garage" ? site?.garage : null;
  const pool = feature.kind === "pool" ? snap.pool : null;
  const boundary = feature.kind === "boundary";
  const surfaceQ = surface ? surfaceQuantities(surface) : null;
  const garageQ = garage ? garageQuantities(garage) : null;
  const boundaryQ = boundary ? polygonQuantities(feature.polygon) : null;
  const palette = snap.material_palette ?? "limestone_oak";
  const basis =
    surface?.input_basis ??
    garage?.input_basis ??
    pool?.input_basis ??
    site?.input_basis ??
    "demonstration_assumption";
  const poolLevel = pool
    ? snap.levels.find((level) => level.id === pool.level_id)
    : null;
  const source = boundary
    ? site?.context_polygon?.length
      ? "Saved study extent"
      : "Model extents + 3 m margin"
    : "Saved design geometry";

  return (
    <section className="site-inspector" aria-label={`${feature.label} details`}>
      <div className="inspector-title">
        <span className="object-symbol">
          <Icon name={garage ? "cube" : "site"} size={28} />
        </span>
        <h2 tabIndex={-1}>{feature.label}</h2>
        <p>
          {boundary
            ? "Assumed study extent"
            : garage
              ? "Detached · Unconditioned"
              : "Outdoor space"}{" "}
          · Revision {snap.revision_number}
        </p>
      </div>

      {!boundary && (
        <div className="site-inspector-materials">
          <h3>Materials & finishes</h3>
          {surface && (
            <Field
              label="Surface"
              value={
                feature.kind === "yard"
                  ? "Grass"
                  : feature.kind === "driveway"
                    ? "Concrete-like paving"
                    : "Stone-like paving"
              }
            />
          )}
          {garage && (
            <>
              <Field label="Exterior walls" value={wallFinishes[palette]} />
              <Field label="Slab & roof" value="Concrete appearance" />
              <Field label="Vehicle door" value="Metal appearance" />
            </>
          )}
          {pool && (
            <>
              <Field label="Basin finish" value="Stone-like appearance" />
              <Field label="Water" value="Illustrative water finish" />
            </>
          )}
          <p className="site-inspector-note">
            {garage
              ? "Finishes are illustrative. Structural grades, reinforcement, insulation and fire performance are not specified."
              : feature.kind === "yard"
                ? "Grass is an illustrative surface. Soil layers, planting and drainage construction are not specified."
                : pool
                  ? "Finishes are illustrative. Basin construction, waterproofing and pool equipment are not specified."
                  : "Paving appearance is illustrative. Build-up, thickness and drainage construction are not specified."}
          </p>
        </div>
      )}

      <div className="properties">
        {surface && surfaceQ && (
          <>
            <Field
              label={
                feature.kind === "yard" ? "Net grass area" : "Net paving area"
              }
              value={areaLabel(surfaceQ.net_area_m2, units)}
            />
            <Field
              label="Gross footprint"
              value={areaLabel(surfaceQ.gross_area_m2, units)}
            />
            {surfaceQ.excluded_area_m2 > 0 && (
              <Field
                label={
                  feature.kind === "yard"
                    ? "Pool & deck excluded"
                    : "Openings excluded"
                }
                value={areaLabel(surfaceQ.excluded_area_m2, units)}
              />
            )}
            <Field label="Width" value={length(surfaceQ.width_m, units)} />
            <Field label="Depth" value={length(surfaceQ.depth_m, units)} />
            <Field
              label="Surface elevation"
              value={elevation(surface.elevation_m, units)}
            />
          </>
        )}
        {garage && garageQ && (
          <>
            <Field
              label="Clear floor area"
              value={areaLabel(garageQ.clear_area_m2, units)}
            />
            <Field
              label="Gross footprint"
              value={areaLabel(garageQ.gross_area_m2, units)}
            />
            <Field
              label="Exterior width × depth"
              value={`${length(garageQ.width_m, units)} × ${length(garageQ.depth_m, units)}`}
            />
            <Field
              label="Clear width × depth"
              value={`${length(garageQ.clear_width_m, units)} × ${length(garageQ.clear_depth_m, units)}`}
            />
            <Field
              label="Wall height to soffit"
              value={length(garage.height_m, units)}
            />
            <Field
              label="Vehicle door width"
              value={length(garage.vehicle_door_width_m, units)}
            />
            <Field
              label="Vehicle door height"
              value={length(garage.vehicle_door_height_m, units)}
            />
            <Field label="Position beside house" value={title(garage.side)} />
          </>
        )}
        {pool && (
          <>
            <Field
              label="Water area"
              value={areaLabel(pool.water_length_m * pool.water_width_m, units)}
            />
            <Field
              label="Water length"
              value={length(pool.water_length_m, units)}
            />
            <Field
              label="Water width"
              value={length(pool.water_width_m, units)}
            />
            <Field
              label="Water depth"
              value={length(pool.water_depth_m, units)}
            />
            <Field
              label="Water volume"
              value={volume(
                pool.water_length_m * pool.water_width_m * pool.water_depth_m,
                units,
              )}
            />
            <Field
              label="Ground datum"
              value={
                poolLevel
                  ? elevation(poolLevel.elevation_m, units)
                  : "Not specified"
              }
            />
          </>
        )}
        {boundaryQ && (
          <>
            <Field
              label="Study area"
              value={areaLabel(boundaryQ.area_m2, units)}
            />
            <Field label="Width" value={length(boundaryQ.width_m, units)} />
            <Field label="Depth" value={length(boundaryQ.depth_m, units)} />
            <Field
              label="Perimeter"
              value={length(boundaryQ.perimeter_m, units)}
            />
          </>
        )}
      </div>

      {garage && (
        <details className="site-inspector-details">
          <summary>Construction dimensions</summary>
          <Field
            label="Wall thickness"
            value={length(garage.wall_thickness_m, units, true)}
          />
          <Field
            label="Slab thickness"
            value={length(garage.slab_thickness_m, units, true)}
          />
          <Field
            label="Roof thickness"
            value={length(garage.roof_thickness_m, units, true)}
          />
          <Field
            label="Overall height"
            value={length(garage.height_m + garage.roof_thickness_m, units)}
          />
          <Field
            label="Slab top elevation"
            value={elevation(garage.elevation_m, units)}
          />
          <p className="site-inspector-note">
            Clear dimensions are measured between wall faces and exclude the
            doorway recess. Thicknesses are concept assumptions, not structural
            sizing.
          </p>
        </details>
      )}

      <details className="site-inspector-basis" open={boundary || undefined}>
        <summary>Geometry & source</summary>
        <Field
          label="Revision"
          value={<span title={snap.revision_id}>{snap.revision_number}</span>}
        />
        <Field label="Input basis" value={title(basis)} />
        <Field label="Source" value={source} />
        <Field
          label="Review"
          value={title(site?.review_status ?? "unreviewed")}
        />
        <p className="site-inspector-note">
          {boundary
            ? "This border encloses the modeled house and outdoor features. It is an assumed study extent, not a surveyed or legal property boundary."
            : "Dimensions come from this revision’s canonical geometry in local metres. Placement and elevations are concept assumptions; parcel fit and engineering requirements remain unverified."}
        </p>
      </details>
    </section>
  );
}
