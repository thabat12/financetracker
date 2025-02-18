import { Text, View, Dimensions } from "react-native";
import React, { useEffect, useState } from "react";
import { Canvas, Circle, Group, Path, Skia, SkPath, Rect } from "@shopify/react-native-skia";
import { StatusBar } from "expo-status-bar";

import Data from "../mock_data/accounts.json";

const getPathCoords = ({x, y, dims} : {x?: number[] | String[], y: number[], dims: Dimension}) => {
  // default safe areas
  const [safeT, safeB] = [10, 10];
  
  // get range for data stream
  let minY = Math.min(...y);
  const range = Math.max(...y) - minY;
  const newRange = dims.height - safeT - safeB;
  let yScaled = y.map((val) => { return ((val - minY) / range) * newRange; });
  x = (x === undefined) ? yScaled.map( () => { return ""; }) : x;
  const tickGap = dims.width / (x.length - 1);

  // time to construct the path
  let points: Vector2D[] = [{ x: 0, y: dims.height - safeT - yScaled[0] }];

  for (let ind = 1; ind < Math.min(x.length, yScaled.length); ind++) {
    if (yScaled[ind] !== undefined) {
      const xCoord = (x[ind] === "number" ? x[ind] as number : ind) * tickGap;
      points.push({x: xCoord, y: dims.height - safeT - yScaled[ind]});
    }
  }

  console.log(points);

  return points;
}

const curvePath = ({points, strategy}: {points: Vector2D[], strategy: String}) => {
  const path = Skia.Path.Make();

  switch (strategy) {
    case "bezier":
      path.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const next = points[i];
        const cp1x = (next.x - prev.x) / 3 + prev.x;
        const cp1y =  (next.y - prev.y) / 3 + prev.y;
        const cp2x = (next.x - prev.x) / 3 * 2 + prev.x;
        const cp2y = (next.y - prev.y) / 3 * 2 + prev.y;
        path.cubicTo(cp1x, cp1y, cp2x, cp2y, next.x, next.y);
      }
      break;
  }

  return path;
}

type Vector2D = {
  x: number,
  y: number
}

type Dimension = {
  width: number;
  height: number;
}

const LineGraph = ({x, y, dims} : {x?: number[] | String[], y: number[], dims: Dimension}) => {

  let {width, height} = dims;
  height = height * 0.33;
  const r = width * 0.33;
  const canvasDims: Dimension = {width, height} as Dimension;

  // Height needs to be normalized to the dimensions on screen
  const points: Vector2D[] = getPathCoords({x, y, dims: canvasDims});
  const strategy = "bezier";
  const path: SkPath = curvePath({points, strategy});

  return (
    <Canvas style={{ width, height }}>
      {/* <Rect x={0} y={0} width={width} height={height} color="gray" /> */}
      <Group blendMode="multiply">
        {/* <Circle cx={r} cy={r} r={r} color="cyan" />
        <Circle cx={width - r} cy={r} r={r} color="magenta" />
        <Circle cx={width / 2} cy={width - r} r={r} color="yellow" /> */}
        <Path style="stroke" path={path} color="lightblue" strokeWidth={5}/>
      </Group>
    </Canvas>
  );
}


export default function Index() {

  const x = Data.map((_, ind) => {
    return (ind + 1).toString();
  });
  const y = Data;

  return (
    <>
      <StatusBar
        translucent={true}
        backgroundColor="transparent"
      />
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <LineGraph
          x={x}
          y={y}
          dims={ Dimensions.get("window") as Dimension }
        />
      </View>
    </>
  );
}
