# Build Script for lt_engine
pyinstaller -y engine.spec "lion_throne"
rm -rf ../lt_engine
mkdir ../lt_engine
mkdir ../lt_engine/lt_engine
mv dist/lt_engine ../lt_engine
cp utilities/audio_dlls/* ../lt_engine
cp utilities/install/double_click_to_play.bat ../lt_engine
# cp autoupdater.exe ../lt_engine/lt_engine
cp autoupdater.py ../lt_engine/lt_engine

# Get version
version="Waffle"
constants="./app/constants.py"
while IFS='=' read -r col1 col2
do
    # echo "$col1"
    # echo "$col2"
    if [ $col1 == "VERSION" ]
    then
        version=$col2
        version=${version:2:${#version}-4}
    fi
done < "$constants"
touch metadata.txt
echo "$version" > metadata.txt
cp metadata.txt ../lt_engine/lt_engine

# Now zip up directory
rm -f ../lt_engine.zip
backup="../lt_engine_v${version}.zip"
rm -f "$backup"
7z a ../lt_engine.zip ../lt_engine
cp ../lt_engine.zip "$backup"

echo Done