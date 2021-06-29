<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0" maxScale="0" version="3.16.6-Hannover" minScale="1e+08">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <temporal mode="0" fetchMode="0" enabled="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <customproperties>
    <property key="WMSBackgroundLayer" value="false"/>
    <property key="WMSPublishDataSourceUrl" value="false"/>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="identify/format" value="Value"/>
  </customproperties>
  <pipe>
    <provider>
      <resampling zoomedInResamplingMethod="nearestNeighbour" enabled="false" maxOversampling="2" zoomedOutResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer nodataColor="" classificationMax="337.5" opacity="1" alphaBand="-1" classificationMin="-1" band="1" type="singlebandpseudocolor">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader classificationMode="1" colorRampType="INTERPOLATED" clip="0" labelPrecision="4" maximumValue="337.5" minimumValue="-1">
          <colorramp name="[source]" type="gradient">
            <prop v="247,251,255,255" k="color1"/>
            <prop v="8,48,107,255" k="color2"/>
            <prop v="0" k="discrete"/>
            <prop v="gradient" k="rampType"/>
            <prop v="0.13;222,235,247,255:0.26;198,219,239,255:0.39;158,202,225,255:0.52;107,174,214,255:0.65;66,146,198,255:0.78;33,113,181,255:0.9;8,81,156,255" k="stops"/>
          </colorramp>
          <item alpha="255" value="-1" label="Teren płaski (-1)" color="#646464"/>
          <item alpha="255" value="0" label="Północ (N) (0° do 22,5°)" color="#ff0004"/>
          <item alpha="255" value="22.5" label="Północny-wschód (NE) (22,5° do 67,5°)" color="#ffcc00"/>
          <item alpha="255" value="67.5" label="Wschód (E) (67,5° do 112,5°)" color="#00ff77"/>
          <item alpha="255" value="112.5" label="Południowy-wschód (SE) (112,5° do 157,5°)" color="#37bf00"/>
          <item alpha="255" value="157.5" label="Południe (S) (157,5° do 202,5°)" color="#00daff"/>
          <item alpha="255" value="202.5" label="Południowy-zachód (SW) (202,5° do 247,5°)" color="#0066ff"/>
          <item alpha="255" value="247.5" label="Zachód (W) (247,5 ° do 292,5°)" color="#7d00ae"/>
          <item alpha="255" value="292.5" label="Północny-zachód (NW) (292,5° do 337,5°)" color="#ff00ff"/>
          <item alpha="255" value="337.5" label="Północ (N) (337,5° do 360°)" color="#ff0004"/>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation saturation="0" colorizeStrength="100" grayscaleMode="0" colorizeOn="0" colorizeGreen="128" colorizeBlue="128" colorizeRed="255"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
