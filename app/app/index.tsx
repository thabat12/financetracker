import { Text, View, Dimensions } from "react-native";
import React, { useEffect, useState } from "react";
import { Canvas, Circle, Group, Path, Skia, SkPath, Rect } from "@shopify/react-native-skia";
import { StatusBar } from "expo-status-bar";

import Data from "../mock_data/accounts.json";


const getPath = ({x, y, dims} : {x?: number[] | String[], y: number[], dims: Dimension}) => {
  // default safe areas
  const [safeT, safeB] = [10, 10];
  
  // get range for data stream
  let [minY, maxY] = [Infinity, -Infinity];
  for (let num of y) {
    if (num < minY) { minY = num; }
    if (num > maxY) { maxY = num; }
  }
  const range = maxY - minY;

  // convert each number into a scale
  let yScaled = y.map((val) => {
    return (val - minY) / range;
  });

  // new y-coord system
  const newRange = dims.height - safeT - safeB;
  yScaled = yScaled.map((val) => {
    return val * newRange;
  });

  // section up x accordingly
  if (x === undefined) {
    x = yScaled.map(() => { return ""; })
  }

  // how many ticks?
  const numTicks = x.length;
  const tickGap = dims.width / (numTicks - 1);

  // time to construct the path
  let path = Skia.Path.Make();
  path.moveTo(0, dims.height - safeT - yScaled[0]);

  for (let ind = 1; ind < Math.min(x.length, yScaled.length); ind++) {
    let xCoord: number = ind;
    if (typeof x[ind] === "number") {
      xCoord = x[ind] as number;
    }
    path.lineTo(xCoord * tickGap, dims.height - safeT - yScaled[ind]);
  }

  return path;
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
  const path: SkPath = getPath({x, y, dims: canvasDims});

  console.log("path is being added now", path);
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
