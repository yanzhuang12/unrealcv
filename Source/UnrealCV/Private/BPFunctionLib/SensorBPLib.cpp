// Weichao Qiu @ 2018
#include "SensorBPLib.h"
#include "UnrealcvServer.h"
#include "FusionCamSensor.h"
#include "Runtime/Engine/Classes/GameFramework/Pawn.h"
#include "Runtime/CoreUObject/Public/UObject/UObjectHash.h"
#include "Runtime/Launch/Resources/Version.h"

TArray<UFusionCamSensor*> USensorBPLib::GetFusionSensorList()
{
	TArray<UFusionCamSensor*> SensorList;

	UWorld* World = FUnrealcvServer::Get().GetWorld();
	if (!World) return SensorList;

	APawn* Pawn = FUnrealcvServer::Get().GetPawn();

	if (IsValid(Pawn))
	{
		TArray<UActorComponent*> PawnComponents = FUnrealcvServer::Get().GetPawn()->K2_GetComponentsByClass(UFusionCamSensor::StaticClass());
		// Make sure the one attached to the pawn is the first one.
		for (UActorComponent* FusionCamSensor : PawnComponents)
		{
			SensorList.Add(Cast<UFusionCamSensor>(FusionCamSensor));
		}
	}

	TArray<UObject*> UObjectList;
	bool bIncludeDerivedClasses = false;
	EObjectFlags ExclusionFlags = EObjectFlags::RF_ClassDefaultObject;
	// EInternalObjectFlags ExclusionInternalFlags = EInternalObjectFlags::AllFlags;
	#if ENGINE_MAJOR_VERSION >= 5 && ENGINE_MINOR_VERSION >= 4
        EInternalObjectFlags ExclusionInternalFlags = EInternalObjectFlags_AllFlags;
    #else
	    EInternalObjectFlags ExclusionInternalFlags = EInternalObjectFlags::AllFlags;
    #endif
	GetObjectsOfClass(UFusionCamSensor::StaticClass(), UObjectList, bIncludeDerivedClasses, ExclusionFlags);

	// Filter out objects not belong to the game world (editor world for example)
	for (UObject* SensorObject : UObjectList)
	{
		UFusionCamSensor *FusionSensor = Cast<UFusionCamSensor>(SensorObject);
		if (FusionSensor->GetWorld() != World) continue;
		if (SensorList.Contains(FusionSensor) == false)
		{
			SensorList.Add(FusionSensor);
		}
	}
	return SensorList;
}

UFusionCamSensor* USensorBPLib::GetSensorById(int SensorId)
{
	FUnrealcvServer::Get().InitWorldController(); // TODO: Move this to SensorHandler

	TArray<UFusionCamSensor*> SensorList = USensorBPLib::GetFusionSensorList();
	if (SensorId < 0 || SensorId >= SensorList.Num()) return nullptr;
	return SensorList[SensorId];
}
